"""Voice activity detection.

Uses Silero VAD when it is installed (pip install silero-vad), and an adaptive energy VAD otherwise.
Both return a per-frame boolean mask on the shared 10 ms feature grid.
"""

import numpy as np

from .features import Features


def energy_vad(
    f: Features, margin_db: float = 14.0, below_speech_db: float = 28.0, floor_db: float = -60.0, hangover: int = 5
) -> np.ndarray:
    noise = np.percentile(f.energy_db, 10)
    speech = np.percentile(f.energy_db, 95)
    # Above the noise floor, but also not far below the speaker's level: breath and strain noise in a
    # block sit ~30 dB under speech and must stay "silence" so the block detector can see them.
    thr = max(noise + margin_db, speech - below_speech_db, floor_db)
    mask = f.energy_db > thr
    # Hangover: bridge dips shorter than `hangover` frames (stop consonants, short gaps between syllables).
    return close_gaps(mask, hangover)


def close_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    out = mask.copy()
    for s, e in runs(~mask):
        if 0 < s and e < len(mask) and e - s <= max_gap:
            out[s:e] = True
    return out


def runs(mask: np.ndarray):
    """Yield (start, end) frame index pairs for each run of True values."""
    m = np.concatenate([[False], mask, [False]]).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def silero_vad(x: np.ndarray, sr: int, f: Features) -> np.ndarray | None:
    try:
        from silero_vad import get_speech_timestamps, load_silero_vad  # type: ignore
        import torch  # type: ignore
    except ImportError:
        return None
    model = load_silero_vad()
    ts = get_speech_timestamps(torch.from_numpy(x), model, sampling_rate=sr, min_silence_duration_ms=80)
    mask = np.zeros(f.n, dtype=bool)
    for seg in ts:
        mask[seg["start"] // f.hop : seg["end"] // f.hop + 1] = True
    return mask


def speech_mask(x: np.ndarray, sr: int, f: Features, backend: str = "auto") -> np.ndarray:
    if backend in ("auto", "silero"):
        m = silero_vad(x, sr, f)
        if m is not None:
            return m
        if backend == "silero":
            raise RuntimeError("silero-vad is not installed")
    return energy_vad(f)
