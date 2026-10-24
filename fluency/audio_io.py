"""Audio decode/encode through ffmpeg, so WhatsApp .opus/.ogg, .m4a, .webm and .wav all work."""

import subprocess

import numpy as np

SR = 16000


def _ffmpeg(args, data: bytes) -> bytes:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        input=data,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def decode(data: bytes, sr: int = SR) -> np.ndarray:
    """Decode any container/codec ffmpeg understands into mono float32 at `sr`."""
    raw = _ffmpeg(["-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"], data)
    return np.frombuffer(raw, dtype=np.float32).copy()


def load(path: str, sr: int = SR) -> np.ndarray:
    with open(path, "rb") as f:
        return decode(f.read(), sr)


def encode(x: np.ndarray, sr: int = SR, fmt: str = "ogg") -> bytes:
    """Encode mono float32 audio. 'ogg' gives Opus-in-Ogg, the format WhatsApp uses for voice notes."""
    codec = {
        "ogg": ["-c:a", "libopus", "-b:a", "32k", "-application", "voip", "-f", "ogg"],
        "wav": ["-c:a", "pcm_s16le", "-f", "wav"],
        "mp3": ["-c:a", "libmp3lame", "-b:a", "64k", "-f", "mp3"],
        "m4a": ["-c:a", "aac", "-b:a", "48k", "-movflags", "frag_keyframe+empty_moov", "-f", "mp4"],
    }[fmt]
    pcm = np.clip(x, -1.0, 1.0).astype(np.float32).tobytes()
    return _ffmpeg(["-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0", *codec, "pipe:1"], pcm)


def save(path: str, x: np.ndarray, sr: int = SR) -> None:
    fmt = path.rsplit(".", 1)[-1].lower()
    fmt = {"opus": "ogg", "oga": "ogg"}.get(fmt, fmt)
    with open(path, "wb") as f:
        f.write(encode(x, sr, fmt))
