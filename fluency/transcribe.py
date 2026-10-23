"""Optional word-level transcription with faster-whisper.

Whisper is trained to write *clean* text, so it tends to drop "ב-ב-" fragments and merge repeated
words. We push it toward verbatim output with a disfluent initial prompt and treat the transcript as
one signal among several: the acoustic detectors in detect.py work even when it is wrong or missing.
"""

from dataclasses import dataclass

import numpy as np

# A prompt written in the style we want back makes Whisper keep fillers and repetitions.
VERBATIM_PROMPT = {
    "he": "אה, אני-אני רוצה, אממ, ל-ל-לבוא מ-מחר. כן, כן, אז ש-שלום.",
    "en": "Um, I-I want, uh, to g-g-go to- to the, um, the store.",
}


@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float = 1.0
    chars: list | None = None  # [(char, start_s, end_s)] when the transcriber provides them (CTC)


class Transcriber:
    def __init__(self, model: str = "small", device: str = "auto", compute_type: str = "int8"):
        from faster_whisper import WhisperModel  # type: ignore

        self.model = WhisperModel(model, device=device, compute_type=compute_type)

    def __call__(self, x: np.ndarray, sr: int, language: str = "he") -> list[Word]:
        assert sr == 16000, "Whisper expects 16 kHz audio"
        segments, _ = self.model.transcribe(
            x,
            language=language,
            word_timestamps=True,
            initial_prompt=VERBATIM_PROMPT.get(language),
            condition_on_previous_text=False,
            vad_filter=False,
            beam_size=5,
        )
        return [
            Word(w.word.strip(), float(w.start), float(w.end), float(w.probability))
            for seg in segments
            for w in (seg.words or [])
            if w.word.strip()
        ]


def load_transcriber(model: str | None):
    """Return a transcriber, or None when transcription is disabled or its library is missing.

    "ctc" (or a wav2vec2 model id prefixed with "ctc:") gives verbatim CTC transcription, which word-guided
    editing needs; anything else is a faster-whisper model name.
    """
    if not model or model == "none":
        return None
    try:
        if model == "ctc" or model.startswith("ctc:"):
            from .ctc import DEFAULT_MODEL, CtcTranscriber

            return CtcTranscriber(model[4:] if model.startswith("ctc:") else DEFAULT_MODEL)
        return Transcriber(model)
    except ImportError:
        return None
