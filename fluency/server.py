"""HTTP API + web app. Run: uvicorn fluency.server:app --host 0.0.0.0 --port 8000

Privacy: audio is processed in memory only. Nothing is written to disk or logged.
"""

import base64
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
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


MIME = {"ogg": "audio/ogg", "wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4"}
MODES = ("gentle", "full", "strong")


def check_key(key: str | None):
    """When FLUENCY_API_KEY is set (the hosted server), only the app that ships the key may call the API."""
    want = os.environ.get("FLUENCY_API_KEY")
    if want and key != want:
        raise HTTPException(401, "bad api key")


def read_audio(data: bytes):
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "recording too long")
    try:
        return audio_io.decode(data)
    except RuntimeError:
        raise HTTPException(415, "could not read this audio file")


@app.get("/api/health")
def health():
    return {"ok": True, "transcription": transcriber() is not None}


@app.post("/api/process_all")
def process_all(
    file: UploadFile = File(...),
    language: str = Form("he"),
    fmt: str = Form("m4a"),
    x_api_key: str | None = Header(None),
):
    """Transcribe once and return the result for every mode, so the app can switch modes instantly."""
    check_key(x_api_key)
    if fmt not in MIME:
        raise HTTPException(400, "bad format")
    x = read_audio(file.file.read(MAX_BYTES + 1))
    tr = transcriber()
    words = tr(x, audio_io.SR, language) if tr else None
    results = {}
    for mode in MODES:
        res = process(x, audio_io.SR, Settings(mode=mode, language=language), transcriber=(lambda *_: words) if words else None)
        results[mode] = {"audio": base64.b64encode(audio_io.encode(res.audio, res.sr, fmt)).decode(),
                         "report": res.report(len(x) / audio_io.SR)}
    return {"mime": MIME[fmt], "transcript": " ".join(w.text for w in words) if words else None, "results": results}


@app.post("/api/process")
def process_audio(
    file: UploadFile = File(...),
    mode: str = Form("gentle"),
    language: str = Form("he"),
    fmt: str = Form("ogg"),
    x_api_key: str | None = Header(None),
):
    check_key(x_api_key)
    if mode not in MODES or fmt not in MIME:
        raise HTTPException(400, "bad mode or format")
    x = read_audio(file.file.read(MAX_BYTES + 1))
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
        "mime": MIME[fmt],
        "report": res.report(len(x) / audio_io.SR),
    }


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
