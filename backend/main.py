import os
import uuid
import tempfile
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

# Lazy-loaded model — downloaded on first use (~150 MB for "base")
_model: WhisperModel | None = None

def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # swap "base" → "small" or "medium" for better quality at the cost of speed
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model()  # warm up at startup
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

history: list[dict] = []


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0", "model": "faster-whisper/base"}


@app.post("/api/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    language: str = Form(default="auto"),
):
    contents = await audio_file.read()
    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        model = get_model()
        lang = None if language == "auto" else language
        segments, info = model.transcribe(tmp_path, language=lang, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        os.unlink(tmp_path)

    record: dict = {
        "id": str(uuid.uuid4()),
        "text": text,
        "language": info.language,
        "duration": round(float(info.duration), 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": audio_file.filename or "audio",
    }
    history.append(record)
    return record


@app.get("/api/history")
async def get_history():
    return history


@app.delete("/api/history/{record_id}")
async def delete_record(record_id: str):
    global history
    before = len(history)
    history = [r for r in history if r["id"] != record_id]
    if len(history) == before:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"deleted": record_id}


@app.delete("/api/history")
async def clear_history():
    history.clear()
    return {"cleared": True}
