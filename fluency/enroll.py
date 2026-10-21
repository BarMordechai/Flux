"""Onboarding: pick the most fluent stretch of a 30-60 s recording as the user's voice reference."""

import numpy as np

from . import features as feat
from .detect import DetectConfig, detect
from .inpaint import VoiceProfile
from .vad import speech_mask


def build_profile(x: np.ndarray, sr: int, target: float = 12.0) -> VoiceProfile:
    """Slide a `target`-second window and keep the one with the most speech and the fewest stutter events."""
    f = feat.compute(x, sr)
    mask = speech_mask(x, sr, f)
    events = detect(x, sr, mask, f, None, DetectConfig(mode="full"))
    total = len(x) / sr
    if total <= target:
        return VoiceProfile(x.copy(), sr)
    best, best_score = 0.0, -np.inf
    for start in np.arange(0, total - target, 0.5):
        a, b = f.frame(start), f.frame(start + target)
        speech = mask[a:b].mean()
        bad = sum(1 for e in events if e.kind in ("repetition", "prolongation", "block") and start <= e.start < start + target)
        score = speech - 0.15 * bad
        if score > best_score:
            best, best_score = start, score
    s = int(best * sr)
    return VoiceProfile(x[s : s + int(target * sr)].copy(), sr)
