import numpy as np
from fastapi.testclient import TestClient

from fluency import audio_io
from fluency.server import app

from synth import SR, W1, W2, fricative, join, silence


def sample():
    return join(silence(0.6), W1(), silence(0.09), fricative(0.9, (4000, 7000)), W2(), silence(0.6))


def test_ogg_roundtrip():
    x = sample()
    y = audio_io.decode(audio_io.encode(x, SR, "ogg"))
    assert abs(len(y) - len(x)) < 0.05 * SR


def test_api_process():
    client = TestClient(app)
    assert client.get("/api/health").json()["ok"]
    assert "שטף" in client.get("/").text
    data = audio_io.encode(sample(), SR, "ogg")
    r = client.post("/api/process", files={"file": ("m.ogg", data, "audio/ogg")}, data={"mode": "full"})
    assert r.status_code == 200
    rep = r.json()["report"]
    assert "prolongation" not in rep["counts"]  # acoustic speech cuts are off by default
    assert rep["output_seconds"] < rep["original_seconds"] - 0.5  # leading/trailing silence trimmed


def test_api_rejects_garbage():
    client = TestClient(app)
    r = client.post("/api/process", files={"file": ("x.ogg", b"not audio", "audio/ogg")})
    assert r.status_code == 415


def test_api_process_all_and_key(monkeypatch):
    client = TestClient(app)
    data = audio_io.encode(sample(), SR, "ogg")
    r = client.post("/api/process_all", files={"file": ("m.ogg", data, "audio/ogg")})
    assert r.status_code == 200
    j = r.json()
    assert set(j["results"]) == {"gentle", "full", "strong"} and j["mime"] == "audio/mp4"
    assert len(audio_io.decode(__import__("base64").b64decode(j["results"]["full"]["audio"]))) > SR
    monkeypatch.setenv("FLUENCY_API_KEY", "k")
    assert client.post("/api/process_all", files={"file": ("m.ogg", data, "audio/ogg")}).status_code == 401
    ok = client.post("/api/process_all", files={"file": ("m.ogg", data, "audio/ogg")}, headers={"X-Api-Key": "k"})
    assert ok.status_code == 200
