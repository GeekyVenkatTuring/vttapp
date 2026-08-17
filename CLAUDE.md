# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app is

VoiceToText (VTT) is a local speech-to-text app with two entry points:

1. **Web UI** — React frontend + FastAPI backend. Record audio in the browser, transcribe via the API, view/export history.
2. **Whispr Daemon** (`backend/daemon.py`) — macOS-only background process. Press Right Option (⌥) once to pop up a small floating bar and start listening; press it again to close the bar, transcribe, and auto-paste into the focused text field via `pbcopy` + AppleScript. (Toggle-based, Wispr Flow / Typeless style — not hold-to-record.)

Both use the same FastAPI backend running `faster-whisper` locally on CPU (no cloud API required). The raw transcript then gets punctuation and capitalization restored by a local **ONNX punctuation model** — see `backend/punctuate.py`.

---

## Running the app

**Backend** (required by both the web UI and the daemon):
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The punctuation model (transcript formatting) is pulled automatically from Hugging Face on first run (~1 GB, cached afterwards). No extra server is needed; if the model can't be loaded the app still works and just returns the raw transcript.

**Frontend** (web UI):
```bash
cd frontend
npm install
npm run dev          # dev server on http://localhost:5173
npm run build        # production build → frontend/dist/
npm run preview      # serve the production build
```

**Whispr Daemon** (macOS only, separate deps):
```bash
cd backend
pip install sounddevice pynput numpy requests
python daemon.py
```
The daemon requires Accessibility permission and Microphone permission on macOS (System Settings → Privacy & Security). It also renders a small Tkinter bar, so run it with a Python build that has Tk (the system/python.org builds and Anaconda both do).

---

## Frontend commands

```bash
npm run lint         # eslint check
npm run build        # tsc type-check + vite build (fails on type errors)
```

---

## Architecture

### Backend (`backend/main.py`)

- FastAPI app with three resource groups: `/api/health`, `/api/transcribe`, `/api/history`
- `WhisperModel` is lazy-loaded at startup and held as a module-level singleton (`_model`)
- Model is currently `"small"` on CPU with `int8` compute — swap to `"base"` (faster) or `"medium"` (more accurate) at the top of `main.py`
- **History is in-memory only** — it resets on every backend restart. The frontend independently persists history to `localStorage` under the key `vtt_history`
- CORS is open to `localhost:5173`, `5174`, `5175` (Vite dev ports)
- After transcription, `_postprocess()` restores punctuation/casing via `punctuate.restore()` and then applies the `_SLASH_RE` substitution — in that order, so casing is settled before slash commands are rebuilt

### Transcript formatting (`backend/punctuate.py`)

- A token-classification model (`1-800-BAD-CODE/xlm-roberta_punctuation_fullstop_truecase`) run via the `punctuators` package on **onnxruntime**. Restores punctuation, capitalization (true-casing) **and** sentence boundaries in one ~0.5s pass — no LLM, no extra server
- Because it only *labels existing words*, it can never add, drop, paraphrase, or "answer" the text, so it does not lose context on long run-on transcripts (the reason the earlier Gemma 3 1B LLM formatter was removed). Verified 100% word retention on a 326-word transcript that collapsed under the LLM
- Input is normalized (lowercase + strip existing punctuation) before inference to avoid double-punctuation artifacts. ~1 GB model, downloaded once from Hugging Face and cached; lazy-loaded and warmed at startup
- **Graceful degradation**: if the package/model is unavailable or inference fails, the raw transcript is returned unchanged — the app never hard-fails on formatting
- Env vars: `VTT_FORMAT=0` disables formatting entirely; `VTT_PUNCT_MODEL` overrides the model

### Frontend (`frontend/src/`)

- Vite proxies all `/api/*` requests to `http://localhost:8000`, so `api.ts` uses relative paths
- `useTranscriptionHistory` hook owns all history state and syncs to `localStorage`; `App.tsx` lifts current-record state up and passes it down
- `AudioRecorder` → uses `MediaRecorder` API → posts `audio/webm` blob to `/api/transcribe` via `api.ts`
- `Waveform` → uses `AudioContext` + `AnalyserNode` on the live `MediaStream` for real-time frequency visualization
- `TranscriptionDisplay` → read-only textarea with copy-to-clipboard and `.txt` export

### Whispr Daemon (`backend/daemon.py`)

- **Toggle flow** (not hold-to-record): press `TRIGGER_KEY` (Right Option, ⌥) once to start recording and show the floating bar; press again to stop, transcribe, and paste. State machine: `idle → recording → transcribing → idle`
- **Threading model** — Tkinter owns the main thread (`WhisprApp.run` → `mainloop`). `pynput`'s keyboard listener and `sounddevice`'s audio callback run on their own threads and never touch Tk directly; they communicate via a `queue.Queue` (`_cmd_q`) that the Tk `_poll` loop drains. Key-repeat is de-duped with the `_alt_down` flag (toggle fires only on the press transition)
- **Floating bar** (`WhisprBar`) — a borderless, always-on-top Tk `Toplevel` pill near the bottom-center of the screen. A `_animate` loop redraws a waveform: while recording the bars track the live mic amplitude (`_level`, an RMS read from the audio callback); while transcribing they show a "thinking" shimmer. The bar is hidden before pasting so focus stays on the target app
- Writes a 16 kHz mono `.wav` to a temp file, POSTs it to the backend, then pastes the formatted result via `pbcopy` + `osascript` Cmd-V
- Configure `LANGUAGE`, `BACKEND_URL`, and `TRIGGER_KEY` via the constants at the top of the file

### Vocabulary tuning (fixing mishearings)

Two mechanisms in `backend/main.py` fix proper-noun and domain-term recognition:

- **Model** — `large-v3` on CPU with `int8` quantization. It has strong proper-noun recognition so terms like "Claude" and "cmux" are handled without any word lists. Swap to `"small"` if startup latency or RAM (~3 GB) is a concern.
- **Slash commands** — `"slash goal"` → `"/goal"` is handled by `_SLASH_RE` post-processing in `_postprocess()`. Whisper always transcribes the spoken word "slash" literally; this one regex is the only post-processing needed.

These fixes apply to both the web UI and the Whispr daemon (the daemon receives already-processed text from the API).

### Type duplication

There are two `TranscriptionRecord` definitions:
- `src/types.ts` — the canonical one (`timestamp: string`, includes `filename?`) — used by all components
- `src/types/transcription.ts` — stale/unused (`timestamp: number`) — can be deleted

All imports should reference `../../types` (or `../types`), not `types/transcription`.
