# VoiceToText (VTT)

Local speech-to-text. Audio never leaves your machine.

There are two ways to use it:

1. **Web UI** — record in the browser, transcribe, copy or export, and keep a history.
2. **Whispr daemon** (macOS) — press Right Option (⌥) to listen, press it again to transcribe and paste into the focused app.

Both talk to the same FastAPI backend. Transcription uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) on CPU. Punctuation and capitalization are restored by a local ONNX token model (not an LLM), so words are not added, dropped, or rewritten.

## Requirements

- Python 3.10+
- Node.js 18+ (web UI only)
- macOS (daemon only): Accessibility + Microphone permissions, and a Python build with Tk

First backend start downloads the Whisper `small` model and the punctuation model (~1 GB, cached after that). If punctuation cannot load, the app still returns the raw transcript.

## Quick start

### 1. Backend (required)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. Web UI

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api/*` to the backend.

Record, pick a language (or auto-detect), then copy or download the text. History is stored in the browser (`localStorage`); the backend’s in-memory history resets on restart.

### 3. Whispr daemon (macOS)

Keep the backend running, then:

```bash
cd backend
pip install sounddevice pynput numpy requests
python daemon.py
```

| Action | Result |
| --- | --- |
| Right Option (⌥) | Start listening (floating bar) |
| Right Option again, or ✓ | Stop, transcribe, paste |
| Escape or ✕ | Cancel and discard |

Grant **Accessibility** (System Settings → Privacy & Security) so paste works, and **Microphone** on first run. Configure `LANGUAGE`, `BACKEND_URL`, and `TRIGGER_KEY` at the top of `backend/daemon.py`.

## How transcription is cleaned up

1. faster-whisper (`small`, CPU, int8) produces the raw text.
2. `backend/punctuate.py` restores punctuation, true-casing, and sentence boundaries (~0.5s).
3. Spoken “slash goal” becomes `/goal` (same for other slash commands).

Disable formatting with `VTT_FORMAT=0`. Override the punctuation model with `VTT_PUNCT_MODEL`.

To trade speed vs accuracy, change the Whisper size in `backend/main.py` (`get_model()`): `"base"` is faster, `"medium"` / `"large-v3"` are more accurate and use more RAM.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Status and model name |
| `POST` | `/api/transcribe` | Upload audio (`audio_file`, optional `language`) |
| `GET` | `/api/history` | In-memory records (this process only) |
| `DELETE` | `/api/history/{id}` | Delete one record |
| `DELETE` | `/api/history` | Clear all |

## Project layout

```
backend/          FastAPI, Whisper, punctuation, Whispr daemon
frontend/         React + Vite + Tailwind web UI
```
