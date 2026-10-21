"""Frame-level acoustic features shared by the VAD and the stutter detectors."""

from dataclasses import dataclass

import numpy as np

FRAME = 0.025  # seconds
HOP = 0.010  # seconds
N_MELS = 40


def _mel(f):
    return 2595.0 * np.log10(1.0 + f / 700.0)


def _mel_inv(m):
    return 700.0 * (10 ** (m / 2595.0) - 1.0)


def mel_filterbank(sr: int, n_fft: int, n_mels: int = N_MELS, fmin=60.0, fmax=None) -> np.ndarray:
    fmax = fmax or sr / 2 - 400
    pts = _mel_inv(np.linspace(_mel(fmin), _mel(fmax), n_mels + 2))
    bins = np.fft.rfftfreq(n_fft, 1 / sr)
    fb = np.zeros((n_mels, len(bins)))
    for i in range(n_mels):
        lo, c, hi = pts[i], pts[i + 1], pts[i + 2]
        up = (bins - lo) / (c - lo)
        down = (hi - bins) / (hi - c)
        fb[i] = np.maximum(0, np.minimum(up, down))
    return fb


@dataclass
class Features:
    sr: int
    hop: int  # samples
    energy_db: np.ndarray  # (T,) frame RMS in dBFS
    logmel: np.ndarray  # (T, N_MELS) log-mel spectrum in dB
    zcr: np.ndarray  # (T,) zero-crossing rate

    @property
    def n(self) -> int:
        return len(self.energy_db)

    def t(self, frame: int) -> float:
        return frame * self.hop / self.sr

    def frame(self, seconds: float) -> int:
        return int(round(seconds * self.sr / self.hop))


def compute(x: np.ndarray, sr: int) -> Features:
    win = int(FRAME * sr)
    hop = int(HOP * sr)
    n_fft = 1 << (win - 1).bit_length()
    pad = np.pad(x, (win // 2, win // 2))
    n = max(1, 1 + (len(pad) - win) // hop)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    frames = pad[idx]
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    energy_db = 20 * np.log10(rms + 1e-9)
    spec = np.abs(np.fft.rfft(frames * np.hanning(win), n=n_fft)) ** 2
    logmel = 10 * np.log10(spec @ mel_filterbank(sr, n_fft).T + 1e-10)
    zcr = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)
    return Features(sr, hop, energy_db, logmel, zcr)


def spectral_change(f: Features, half: int = 5) -> np.ndarray:
    """Mean absolute dB difference between the average spectrum just before and just after each frame.

    Steady sounds (a held vowel or a prolonged 'ssss') score low; running speech scores high.
    Averaging over `half` frames on each side keeps noise-like fricatives from looking unstable.
    """
    c = np.cumsum(np.vstack([np.zeros((1, f.logmel.shape[1])), f.logmel]), axis=0)
    out = np.full(f.n, np.inf)
    for t in range(half, f.n - half):
        before = (c[t] - c[t - half]) / half
        after = (c[t + half] - c[t]) / half
        out[t] = np.mean(np.abs(after - before))
    return out
