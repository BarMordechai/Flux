"""HTTP API + web app. Run: uvicorn fluency.server:app --host 0.0.0.0 --port 8000

Privacy: audio is processed in memory only. Nothing is written to disk or logged.
"""

import base64
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import audio_io
from .inpaint import load_inpainter
from .pipeline import Settings, process
from .transcribe import load_transcriber

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_BYTES = 20 * 1024 * 1024  # ~ a 15-minute voice note

app = FastAPI(title="Fluency", docs_url="/api/docs")


@lru_cache(maxsize=1)
def transcriber():
    return load_transcriber(os.environ.get("FLUENCY_WHISPER_MODEL", "none"))


@app.get("/api/health")
def health():
    return {"ok": True, "transcription": transcriber() is not None}


@app.post("/api/process")
async def process_audio(
    file: UploadFile = File(...),
    mode: str = Form("gentle"),
    language: str = Form("he"),
    fmt: str = Form("ogg"),
):
    if mode not in ("gentle", "full") or fmt not in ("ogg", "wav", "mp3"):
        raise HTTPException(400, "bad mode or format")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "recording too long")
    try:
        x = audio_io.decode(data)
    except RuntimeError:
        raise HTTPException(415, "could not read this audio file")
    res = process(
        x,
        audio_io.SR,
        Settings(mode=mode, language=language),
        transcriber=transcriber(),
        inpainter=load_inpainter(os.environ.get("FLUENCY_INPAINTER", "none")),
    )
    out = audio_io.encode(res.audio, res.sr, fmt)
    return {
        "audio": base64.b64encode(out).decode(),
        "mime": {"ogg": "audio/ogg", "wav": "audio/wav", "mp3": "audio/mpeg"}[fmt],
        "report": res.report(len(x) / audio_io.SR),
    }


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
