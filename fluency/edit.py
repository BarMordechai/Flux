"""Remove intervals from audio and join what is left with short raised-cosine cross-fades."""

import numpy as np


def merge(cuts, min_len: float = 0.01):
    out = []
    for a, b in sorted(c for c in cuts if c[1] - c[0] >= min_len):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(c) for c in out]


def _quiet_point(x: np.ndarray, i: int, radius: int) -> int:
    """Move a cut point to the lowest-energy sample nearby, so joins land between pitch pulses."""
    lo, hi = max(0, i - radius), min(len(x), i + radius)
    if hi - lo < 4:
        return i
    env = np.convolve(np.abs(x[lo:hi]), np.ones(32) / 32, mode="same")
    return lo + int(np.argmin(env))


def apply_cuts(x: np.ndarray, sr: int, cuts, xfade: float = 0.015):
    """Return (audio, joins) where joins are the output times (s) of each splice."""
    cuts = merge(cuts)
    n_xf = int(xfade * sr)
    radius = int(0.004 * sr)
    keep, pos = [], 0
    for a, b in cuts:
        ia = _quiet_point(x, int(a * sr), radius)
        ib = _quiet_point(x, int(b * sr), radius)
        if ia > pos:
            keep.append((pos, ia))
        pos = max(pos, ib)
    if pos < len(x):
        keep.append((pos, len(x)))
    if not keep:
        return np.zeros(0, dtype=np.float32), []

    out = x[keep[0][0] : keep[0][1]].astype(np.float32)
    joins = []
    for s, e in keep[1:]:
        seg = x[s:e].astype(np.float32)
        n = min(n_xf, len(out), len(seg))
        fi = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
        mixed = out[len(out) - n :] * (1 - fi) + seg[:n] * fi
        joins.append((len(out) - n / 2) / sr)
        out = np.concatenate([out[: len(out) - n], mixed, seg[n:]])
    return out, joins
