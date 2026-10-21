"""Hook for regenerating audio around splices in the user's own voice.

Cutting plus cross-fading (edit.py) already covers most repetitions, prolongations and blocks. The
remaining cases need *new* audio: a word cut off by a block, or a splice whose pitch jump is audible.
That is a speech-editing job for a zero-shot voice model conditioned on the user's VoiceProfile.

Candidate open models to plug in here (check each licence before commercial use):
  * F5-TTS / E2-TTS: flow-matching TTS with infilling; reference audio + text in, speech out.
  * VoiceCraft: token-infilling speech editor built on EnCodec, the closest match to the spec.
  * CosyVoice 2 / XTTS-v2: zero-shot cloning; regenerate a whole short word and splice it in.
Hebrew support is the gating factor; expect to fine-tune on ivrit.ai data.
"""

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .transcribe import Word


@dataclass
class VoiceProfile:
    """What a zero-shot voice model needs: a clean reference clip of the user and its transcript."""

    reference: np.ndarray
    sr: int
    text: str = ""


class Inpainter(Protocol):
    def refine(
        self, audio: np.ndarray, sr: int, joins: list[float], words: list[Word] | None, voice: VoiceProfile | None
    ) -> np.ndarray:
        """Return audio with the region around each join (output seconds) regenerated, or unchanged."""


class NullInpainter:
    """Default: keep the cross-faded splice as is."""

    def refine(self, audio, sr, joins, words, voice):
        return audio


_REGISTRY: dict[str, type] = {"none": NullInpainter}


def register(name: str):
    def deco(cls):
        _REGISTRY[name] = cls
        return cls

    return deco


def load_inpainter(name: str = "none") -> Inpainter:
    if name not in _REGISTRY:
        raise ValueError(f"unknown inpainter '{name}', available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()
