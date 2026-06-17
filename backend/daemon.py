#!/usr/bin/env python3
"""
Whispr-style voice input daemon for macOS (Wispr Flow / Typeless style).

Press Right Option (⌥) once  → a small bar pops up and starts listening.
Press Right Option (⌥) again → the bar closes, the audio is transcribed,
                               formatted, and pasted into the focused app.

The backend transcribes with faster-whisper and then reformats the raw text
with a local LLM (Gemma 3 1B via Ollama) so the pasted result has proper
punctuation and capitalization.

Requires one-time macOS permissions:
  - Accessibility  (System Settings → Privacy & Security → Accessibility)
  - Microphone     (granted automatically on first run)
"""

import os
import sys
import math
import wave
import queue
import threading
import subprocess
import tempfile

import numpy as np
import requests
import sounddevice as sd
from pynput import keyboard
import tkinter as tk

BACKEND_URL = "http://localhost:8000/api/transcribe"
SAMPLE_RATE = 16000
CHANNELS = 1
LANGUAGE = "auto"               # "hi" to force Hindi, "auto" to auto-detect
TRIGGER_KEY = keyboard.Key.alt_r  # Right Option (⌥). Use Key.alt_l for Left Option.

# ── shared state (touched from the audio + keyboard threads) ──────────────────
STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_TRANSCRIBING = "transcribing"

_state = STATE_IDLE
_audio_frames: list = []
_level = 0.0                    # live mic amplitude 0..1, drives the waveform
_lock = threading.Lock()
_cmd_q: "queue.Queue" = queue.Queue()
_alt_down = False               # dedupe key-repeat while the key is held


# ── notifications + paste ─────────────────────────────────────────────────────
def _notify(title: str, message: str):
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        capture_output=True,
    )


def _paste_text(text: str):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "v" using command down'],
        check=True,
    )


# ── audio ─────────────────────────────────────────────────────────────────────
def _audio_callback(indata, frames, time_info, status):
    global _level
    if _state == STATE_RECORDING:
        _audio_frames.append(indata.copy())
        rms = float(np.sqrt(np.mean(np.square(indata))))
        # smooth the level a little so the bars don't jitter
        _level = max(_level * 0.6, min(1.0, rms * 9))
    else:
        _level *= 0.6


def _transcribe(frames: list) -> str:
    """POST recorded frames to the backend and return the formatted text."""
    if not frames:
        return ""

    audio_data = np.concatenate(frames, axis=0)
    duration = len(audio_data) / SAMPLE_RATE
    if duration < 0.4:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())

        with open(tmp_path, "rb") as f:
            resp = requests.post(
                BACKEND_URL,
                files={"audio_file": ("audio.wav", f, "audio/wav")},
                data={"language": LANGUAGE},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    finally:
        os.unlink(tmp_path)


def _transcribe_worker(frames: list):
    """Runs off the UI thread: transcribe, then report back via the queue."""
    try:
        text = _transcribe(frames)
        _cmd_q.put(("result", text))
    except requests.exceptions.ConnectionError:
        _cmd_q.put(("error", "Backend not running on port 8000"))
    except Exception as exc:  # noqa: BLE001
        _cmd_q.put(("error", str(exc)[:120]))


# ── keyboard ──────────────────────────────────────────────────────────────────
def on_press(key):
    global _alt_down
    if key == TRIGGER_KEY and not _alt_down:
        _alt_down = True
        _cmd_q.put(("toggle", None))


def on_release(key):
    global _alt_down
    if key == TRIGGER_KEY:
        _alt_down = False


# ── floating bar UI ───────────────────────────────────────────────────────────
class WhisprBar:
    """A small always-on-top pill that visualizes listening / transcribing."""

    W, H = 240, 60
    N_BARS = 15
    BG = "#181a1f"
    ACCENT = "#5b8cff"
    ACCENT_REC = "#ff5b6e"
    TEXT = "#c8ccd4"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.win = None
        self.canvas = None
        self.bars = []
        self.dot = None
        self.label = None
        self._phase = 0.0

    def _build(self):
        if self.win is not None:
            return
        self.win = tk.Toplevel(self.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = (sw - self.W) // 2
        y = sh - self.H - 90
        self.win.geometry(f"{self.W}x{self.H}+{x}+{y}")

        self.canvas = tk.Canvas(
            self.win, width=self.W, height=self.H,
            bg=self.BG, highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._round_rect(2, 2, self.W - 2, self.H - 2, 16, fill=self.BG)

        # recording dot on the left
        self.dot = self.canvas.create_oval(16, self.H / 2 - 5, 26, self.H / 2 + 5,
                                            fill=self.ACCENT_REC, outline="")

        # waveform bars in the middle
        cx = self.W / 2 + 6
        spacing = 9
        start = cx - (self.N_BARS - 1) * spacing / 2
        for i in range(self.N_BARS):
            bx = start + i * spacing
            bar = self.canvas.create_line(bx, self.H / 2 - 3, bx, self.H / 2 + 3,
                                          fill=self.ACCENT, width=4, capstyle="round")
            self.bars.append(bar)

        self.label = self.canvas.create_text(
            self.W - 16, self.H / 2, anchor="e",
            text="", fill=self.TEXT, font=("Helvetica", 11),
        )

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def show(self):
        self._build()
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        if self.win is not None:
            self.win.withdraw()

    def render(self, state: str):
        """Called on every animation tick from the main thread."""
        if self.win is None or state == STATE_IDLE:
            return
        self._phase += 0.35
        cy = self.H / 2

        if state == STATE_RECORDING:
            self.canvas.itemconfig(self.dot, fill=self.ACCENT_REC)
            self.canvas.itemconfig(self.label, text="Listening…")
            base = _level
            for i, bar in enumerate(self.bars):
                # blend the live mic level with a travelling sine for liveliness
                wob = 0.5 + 0.5 * math.sin(self._phase + i * 0.6)
                amp = (0.18 + 0.82 * base) * wob
                h = 3 + amp * (self.H / 2 - 8)
                bx = self.canvas.coords(bar)[0]
                self.canvas.coords(bar, bx, cy - h, bx, cy + h)
                self.canvas.itemconfig(bar, fill=self.ACCENT_REC)
        else:  # transcribing — gentle "thinking" shimmer
            self.canvas.itemconfig(self.dot, fill=self.ACCENT)
            self.canvas.itemconfig(self.label, text="Transcribing…")
            for i, bar in enumerate(self.bars):
                wob = 0.5 + 0.5 * math.sin(self._phase * 1.4 + i * 0.9)
                h = 3 + wob * (self.H / 2 - 16)
                bx = self.canvas.coords(bar)[0]
                self.canvas.coords(bar, bx, cy - h, bx, cy + h)
                self.canvas.itemconfig(bar, fill=self.ACCENT)


class WhisprApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # no main window, only the floating bar
        self.bar = WhisprBar(self.root)

    # ---- command handling -----------------------------------------------------
    def _handle(self, cmd, payload):
        global _state
        if cmd == "toggle":
            if _state == STATE_IDLE:
                self._start_recording()
            elif _state == STATE_RECORDING:
                self._stop_and_transcribe()
            # ignore toggles while transcribing
        elif cmd == "result":
            self._finish(payload)
        elif cmd == "error":
            _state = STATE_IDLE
            self.bar.hide()
            print(f"❌ {payload}")
            _notify("Whispr Error", payload)

    def _start_recording(self):
        global _state
        with _lock:
            _audio_frames.clear()
            _state = STATE_RECORDING
        self.bar.show()
        print("🎤 Listening… (press ⌥ again to stop)")

    def _stop_and_transcribe(self):
        global _state
        with _lock:
            frames = list(_audio_frames)
            _state = STATE_TRANSCRIBING
        secs = len(np.concatenate(frames)) / SAMPLE_RATE if frames else 0.0
        print(f"⏳ Transcribing {secs:.1f}s…")
        threading.Thread(target=_transcribe_worker, args=(frames,), daemon=True).start()

    def _finish(self, text: str):
        global _state
        _state = STATE_IDLE
        self.bar.hide()
        self.root.update_idletasks()
        if text:
            _paste_text(text)
            print(f"✅ {text}")
        else:
            print("⚠  No speech detected.")

    # ---- loops ----------------------------------------------------------------
    def _poll(self):
        try:
            while True:
                cmd, payload = _cmd_q.get_nowait()
                self._handle(cmd, payload)
        except queue.Empty:
            pass
        self.root.after(30, self._poll)

    def _animate(self):
        self.bar.render(_state)
        self.root.after(45, self._animate)

    def run(self):
        self._poll()
        self._animate()
        self.root.mainloop()


def main():
    print("🎙  Whispr Daemon started (toggle mode).")
    print("    Press Right Option (⌥) to start listening, press again to transcribe & paste.")
    print("    Press Ctrl+C in this terminal to quit.\n")

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS,
        dtype="float32", callback=_audio_callback,
    )
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    try:
        stream.start()
        listener.start()
        WhisprApp().run()
    except KeyboardInterrupt:
        print("\n👋 Daemon stopped.")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Fatal: {exc}")
        sys.exit(1)
    finally:
        listener.stop()
        stream.stop()
        stream.close()


if __name__ == "__main__":
    main()
