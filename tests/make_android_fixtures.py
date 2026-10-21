"""Write WAV fixtures + expected results so the Kotlin port (android/) is tested against this Python pipeline."""

import io
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
from fluency import Settings, process  # noqa: E402
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
    "sound_repetition": lambda: join(silence(0.2), W1(), silence(G), frag(), silence(0.18), frag(), silence(0.18), frag(),
                                     silence(0.18), W2(), silence(0.2)),
}


def to_pcm16(x):
    return (np.clip(x, -1, 1) * 32767).astype("<i2")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, make in CASES.items():
        pcm = to_pcm16(make())
        with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
        x = pcm.astype(np.float32) / 32768.0
        for mode in ("gentle", "full", "strong"):
            res = process(x, SR, Settings(mode=mode, vad="energy"))
            kinds = ",".join(e.kind for e in res.events) or "-"
            lines.append(f"{name} {mode} {len(res.audio)} {kinds}")
    (OUT / "expected.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
