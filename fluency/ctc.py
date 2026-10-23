"""Verbatim word-level transcription with a CTC (wav2vec2) model.

Unlike Whisper, a CTC model has no language model that "cleans up" the text: it writes what was said,
repetitions and fragments included, and every character comes with the 20 ms frame it was emitted on.
That is exactly what word-guided editing needs. The default model is a Hebrew wav2vec2 XLS-R fine-tune.

decode_words() is plain numpy so the Android app can run the same logic on ONNX output.
"""

import numpy as np

from .transcribe import Word

DEFAULT_MODEL = "imvladikon/wav2vec2-xls-r-300m-hebrew"
FRAME = 0.02  # seconds per CTC output frame for wav2vec2 at 16 kHz


def decode_words(logits: np.ndarray, vocab: list[str], blank: int, delimiter: str = "|") -> list[Word]:
    """Greedy CTC decode into words with times. A word spans from its first to its last emitted character."""
    ids = logits.argmax(axis=1)
    words, chars, prev = [], [], -1

    def flush():
        if chars:
            text = "".join(c for c, _, _ in chars)
            spans = [(c, a * FRAME, (b + 1) * FRAME) for c, a, b in chars]
            words.append(Word(text, spans[0][1], spans[-1][2], chars=spans))
            chars.clear()

    for t, i in enumerate(ids):
        if i == prev:
            if i != blank and vocab[i] != delimiter and chars:
                chars[-1] = (chars[-1][0], chars[-1][1], t)  # character held over several frames
            continue
        prev = i
        if i == blank:
            continue
        tok = vocab[i]
        if tok == delimiter or tok.isspace():
            flush()
        elif not tok.startswith("<"):
            chars.append((tok, t, t))
    flush()
    return words


class CtcTranscriber:
    def __init__(self, model: str = DEFAULT_MODEL):
        import torch  # type: ignore
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor  # type: ignore

        self.torch = torch
        self.processor = Wav2Vec2Processor.from_pretrained(model)
        self.model = Wav2Vec2ForCTC.from_pretrained(model).eval()
        vocab = self.processor.tokenizer.get_vocab()
        self.vocab = [t for t, _ in sorted(vocab.items(), key=lambda kv: kv[1])]
        self.blank = self.processor.tokenizer.pad_token_id
        self.delimiter = getattr(self.processor.tokenizer, "word_delimiter_token", "|") or "|"

    def logits(self, x: np.ndarray, sr: int) -> np.ndarray:
        assert sr == 16000
        out = []
        step = 30 * sr  # 30 s chunks keep memory flat on long messages
        for s in range(0, len(x), step):
            inp = self.processor(x[s : s + step], sampling_rate=sr, return_tensors="pt")
            with self.torch.no_grad():
                out.append(self.model(inp.input_values).logits[0].numpy())
        return np.concatenate(out) if out else np.zeros((0, len(self.vocab)))

    def __call__(self, x: np.ndarray, sr: int, language: str = "he") -> list[Word]:
        return decode_words(self.logits(x, sr), self.vocab, self.blank, self.delimiter)
