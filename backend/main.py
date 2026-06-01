import os
import uuid
import tempfile
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import openai

load_dotenv()

app = FastAPI()

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
    return {"status": "ok", "version": "1.0"}


@app.post("/api/transcribe")
async def transcribe(
    audio_file: UploadFile = File(...),
    language: str = Form(default="auto"),
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=422, detail="OPENAI_API_KEY is not set")

    contents = await audio_file.read()

    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        client = openai.OpenAI(api_key=api_key)
        with open(tmp_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=None if language == "auto" else language,
                response_format="verbose_json",
            )
    finally:
        os.unlink(tmp_path)

    record: dict = {
        "id": str(uuid.uuid4()),
        "text": response.text,
        "language": getattr(response, "language", language),
        "duration": float(getattr(response, "duration", 0.0)),
        "timestamp": datetime.utcnow().isoformat(),
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
