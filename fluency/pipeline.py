"""End-to-end offline pipeline: audio in, smoothed audio + report out."""

from dataclasses import dataclass, field

import numpy as np

from . import features as feat
from .detect import DetectConfig, Event, detect
from .edit import apply_cuts
from .inpaint import Inpainter, NullInpainter, VoiceProfile
from .transcribe import Transcriber, Word
from .vad import speech_mask


@dataclass
class Settings:
    mode: str = "gentle"  # gentle | full
    language: str = "he"
    vad: str = "auto"  # auto | silero | energy
    detect: DetectConfig | None = None

    def detect_config(self) -> DetectConfig:
        cfg = self.detect or DetectConfig()
        cfg.mode = self.mode
        return cfg


@dataclass
class ProcessResult:
    audio: np.ndarray
    sr: int
    events: list[Event]
    words: list[Word] | None
    joins: list[float] = field(default_factory=list)

    def report(self, original_seconds: float) -> dict:
        counts: dict[str, int] = {}
        for e in self.events:
            counts[e.kind] = counts.get(e.kind, 0) + 1
        return {
            "original_seconds": round(original_seconds, 2),
            "output_seconds": round(len(self.audio) / self.sr, 2),
            "counts": counts,
            "events": [e.as_dict() for e in self.events],
            "transcript": " ".join(w.text for w in self.words) if self.words else None,
        }


def process(
    x: np.ndarray,
    sr: int,
    settings: Settings | None = None,
    transcriber: Transcriber | None = None,
    inpainter: Inpainter | None = None,
    voice: VoiceProfile | None = None,
) -> ProcessResult:
    settings = settings or Settings()
    x = x.astype(np.float32)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak < 1e-4:
        return ProcessResult(x, sr, [], None)

    f = feat.compute(x, sr)
    mask = speech_mask(x, sr, f, settings.vad)
    words = transcriber(x, sr, settings.language) if transcriber else None
    events = detect(x, sr, mask, f, words, settings.detect_config())
    out, joins = apply_cuts(x, sr, [e.cut for e in events if e.cut])
    out = (inpainter or NullInpainter()).refine(out, sr, joins, words, voice)
    return ProcessResult(out, sr, events, words, joins)
