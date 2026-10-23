"""Write WAV fixtures + expected results so the Kotlin port (android/) is tested against this Python pipeline."""

import io
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from fluency import Settings, process  # noqa: E402
from fluency.transcribe import Word  # noqa: E402
from synth import SR, W1, W2, W3, fricative, join, silence, syllable, vowel  # noqa: E402

OUT = Path(__file__).parent.parent / "android/app/src/test/resources/fixtures"
G = 0.09


def frag():
    return syllable((1000, 2500), "o", dur=0.12)


CASES = {
    "fluent": lambda: join(silence(0.2), W1(), silence(G), W2(), silence(G), W3(), silence(0.2)),
    "long_pause": lambda: join(silence(0.2), W1(), silence(G), W2(), silence(2.5), W3(), silence(0.2)),
    "fricative_prolongation": lambda: join(silence(0.2), W1(), silence(G), fricative(0.9, (4000, 7000)), W2(), silence(0.2)),
    "vowel_prolongation": lambda: join(silence(0.2), W1(), silence(G), vowel("a", 1.0, f0=(130, 130)), W3(), silence(0.2)),
    "block_strain": lambda: join(silence(0.2), W1(), silence(G),
                                 (0.0015 * np.random.default_rng(1).standard_normal(int(1.2 * SR))).astype(np.float32),
                                 W2(), silence(0.2)),
    "word_repetition": lambda: join(silence(0.2), W1(), silence(0.15), W1(), silence(0.15), W2(), silence(G), W3(),
                                    silence(0.2)),
    "sound_repetition": lambda: join(silence(0.2), W1(), silence(G), frag(), silence(0.18), frag(), silence(0.18), frag(),
                                     silence(0.18), W2(), silence(0.2)),
}


def _d(a):
    return len(a) / SR


def word_cases():
    """Cases with a (hand-made) CTC transcript, for the word-guided editing path."""
    w1, w2, w3, fr = W1(), W2(), W3(), fricative(0.9, (4000, 7000))
    out = {}

    # "אני אני רוצה": a whole-word repetition
    x = join(silence(0.2), w1, silence(0.15), w1, silence(0.15), w2, silence(0.2))
    s2 = 0.2 + _d(w1) + 0.15
    s3 = s2 + _d(w1) + 0.15
    out["t_word_repetition"] = (x, [Word("אני", 0.25, 0.2 + _d(w1), chars=[("א", 0.25, 0.27), ("נ", 0.4, 0.42)]),
                                    Word("אני", s2 + 0.05, s2 + _d(w1), chars=[("א", s2 + 0.05, s2 + 0.07)]),
                                    Word("רוצה", s3 + 0.05, s3 + _d(w2), chars=[("ר", s3 + 0.05, s3 + 0.07)])])
    # "ב בית": a one-letter fragment
    frag = syllable((1000, 2500), "o", dur=0.12)
    x = join(silence(0.2), frag, silence(0.2), w2, silence(0.2))
    s2 = 0.2 + _d(frag) + 0.2
    out["t_fragment"] = (x, [Word("ב", 0.22, 0.2 + _d(frag), chars=[("ב", 0.22, 0.24)]),
                             Word("בית", s2 + 0.04, s2 + _d(w2), chars=[("ב", s2 + 0.04, s2 + 0.06), ("י", s2 + 0.2, s2 + 0.22)])])
    # "ssssss-shalom": a held sound before the word's first character
    x = join(silence(0.2), w1, silence(0.09), fr, w3, silence(0.2))
    s2 = 0.2 + _d(w1) + 0.09
    s3 = s2 + _d(fr)
    out["t_prolongation"] = (x, [Word("כן", 0.22, 0.2 + _d(w1), chars=[("כ", 0.22, 0.24), ("ן", 0.4, 0.42)]),
                                 Word("שלום", s3 - 0.02, s3 + _d(w3), chars=[("ש", s3 - 0.02, s3), ("ל", s3 + 0.1, s3 + 0.12)])])
    # fluent speech with a correct transcript must stay untouched
    x = join(silence(0.2), w1, silence(0.09), w2, silence(0.09), w3, silence(0.2))
    t1 = 0.2 + _d(w1) + 0.09
    t2 = t1 + _d(w2) + 0.09
    out["t_fluent"] = (x, [Word("אני", 0.22, 0.2 + _d(w1), chars=[("א", 0.22, 0.24)]),
                           Word("רוצה", t1 + 0.02, t1 + _d(w2), chars=[("ר", t1 + 0.02, t1 + 0.04)]),
                           Word("ללכת", t2 + 0.02, t2 + _d(w3), chars=[("ל", t2 + 0.02, t2 + 0.04)])])
    return out


def write_words(path, words):
    with open(path, "w", encoding="utf-8") as fh:
        for w in words:
            chars = "|".join(f"{c}:{a:.4f}:{b:.4f}" for c, a, b in w.chars)
            fh.write(f"{w.text}\t{w.start:.4f}\t{w.end:.4f}\t{chars}\n")


def to_pcm16(x):
    return (np.clip(x, -1, 1) * 32767).astype("<i2")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    cases = {name: (make(), None) for name, make in CASES.items()}
    cases.update(word_cases())
    for name, (audio, words) in cases.items():
        pcm = to_pcm16(audio)
        with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
        if words:
            write_words(OUT / f"{name}.words", words)
        x = pcm.astype(np.float32) / 32768.0
        for mode in ("gentle", "full", "strong"):
            res = process(x, SR, Settings(mode=mode, vad="energy"), transcriber=(lambda *_: words) if words else None)
            kinds = ",".join(e.kind for e in res.events) or "-"
            lines.append(f"{name} {mode} {len(res.audio)} {kinds}")
    (OUT / "expected.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
