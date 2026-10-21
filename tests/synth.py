"""Synthetic speech-like signals with known stutter events, for testing without real recordings."""

import numpy as np

SR = 16000
VOWELS = {"a": (750, 1200), "e": (500, 1900), "i": (300, 2300), "o": (500, 900), "u": (350, 800)}
rng = np.random.default_rng(7)


def _env(n, attack=0.015):
    a = min(int(attack * SR), n // 2)
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    e[n - a :] = np.linspace(1, 0, a)
    return e


def vowel(v: str, dur: float, f0=(120, 150)) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.linspace(*f0, n)
    phase = 2 * np.pi * np.cumsum(f) / SR
    F1, F2 = VOWELS[v]
    y = np.zeros(n)
    for k in range(1, 40):
        fk = k * f.mean()
        amp = np.exp(-((fk - F1) / 120) ** 2) + 0.6 * np.exp(-((fk - F2) / 180) ** 2) + 0.02
        y += amp * np.sin(k * phase)
    return 0.15 * y / np.max(np.abs(y)) * _env(n) + 0 * t


def fricative(dur: float, band=(3500, 7000)) -> np.ndarray:
    n = int(dur * SR)
    spec = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    spec[(fr < band[0]) | (fr > band[1])] = 0
    y = np.fft.irfft(spec, n)
    return 0.06 * y / np.max(np.abs(y)) * _env(n)


def syllable(cons_band, v, dur=0.18, f0=(120, 150)):
    c = fricative(0.05, cons_band) if cons_band else np.zeros(0)
    return np.concatenate([c, vowel(v, dur, f0)])


def silence(dur: float, level: float = 0.0005) -> np.ndarray:
    return level * rng.standard_normal(int(dur * SR))


def word(*sylls):
    return np.concatenate(sylls)


def W1():
    return word(syllable((2000, 4000), "a"), syllable((4000, 7000), "i", f0=(150, 110)))


def W2():
    return word(syllable((1000, 2500), "o"), syllable((3000, 6000), "e", f0=(140, 120)))


def W3():
    return word(syllable((5000, 7500), "u"), syllable((1500, 3000), "a", f0=(130, 100)))


def join(*parts):
    return np.concatenate(parts).astype(np.float32)
