"""Stutter event detection: repetitions, prolongations and blocks.

Every detector returns Events that carry the interval to remove (`cut`). Detection is deliberately
conservative: cutting fluent speech is far worse for the user than leaving a stutter in.
"""

import bisect
import re
from dataclasses import dataclass, field, replace

import numpy as np

from . import features as feat
from .transcribe import Word
from .vad import runs


@dataclass
class ModeSettings:
    prolong_min: float  # shortest steady sound treated as a prolongation (s)
    prolong_keep: float  # how much of a prolonged sound to keep (s)
    block_min: float  # shortest mid-phrase gap that can be a block (s)
    block_keep: float  # silence left where a block was (s)
    pause_max: float  # natural pauses longer than this are shortened (s)
    pause_keep: float  # ...down to this (s)
    keep_one_repetition: bool  # leave a single repetition in, so the result still sounds human
    fragment_max: float = 0.35  # a burst shorter than this can be a part-word repetition (s)
    fragment_gap_max: float = 0.6  # longest gap between a fragment and its repeat (s)
    fragment_sim_db: float = 4.0  # spectral distance below which a fragment matches the next onset
    steady_db: float = 2.2  # spectral change below which a frame counts as a steady sound (calibrate on real data)
    word_dtw_db: float = 0.0  # DTW distance below which a word-length chunk repeats the next one; 0 disables
    word_max: float = 0.8  # longest chunk checked as a repeated word (s)
    word_gap_max: float = 0.5  # longest gap between a word and its repeat (s)


# Calibrated on SEP-28k (tools/calibrate_sep28k.py, 40 episodes / 2,799 clips). Fields after the first seven:
# fragment_max, fragment_gap_max, fragment_sim_db, steady_db, word_dtw_db, word_max, word_gap_max.
MODES = {
    "gentle": ModeSettings(0.30, 0.20, 0.35, 0.25, 1.6, 0.9, True, 0.35, 0.6, 4.0, 2.8, 3.0, 0.8, 0.5),
    "full": ModeSettings(0.22, 0.12, 0.25, 0.12, 1.0, 0.55, False, 0.25, 0.4, 5.5, 2.8, 3.0, 0.8, 0.8),
    # Strong: looser detectors and harder compression, for users who prefer fewer misses over naturalness.
    "strong": ModeSettings(0.22, 0.08, 0.18, 0.08, 0.7, 0.4, False, 0.35, 0.6, 5.5, 3.4, 3.5, 0.8, 0.8),
}


@dataclass
class DetectConfig:
    mode: str = "gentle"
    edge_keep: float = 0.25  # silence kept at the start/end of the message (s)
    # Acoustic repetition/prolongation detectors cannot tell a stutter from a real word reliably (users heard whole
    # words cut), so by default they only inform block detection and nothing they find is removed.
    acoustic_speech_cuts: bool = False
    # A transcript repetition is only cut if the removed audio really sounds like the word that is kept (DTW
    # distance below this); guards against the recogniser hallucinating a repeat. 0 disables the check.
    verify_repetition_db: float = 4.5
    # Anchored repetitions: speech chunks just before a recognised word that sound like that word's onset.
    # Whisper writes the word once even when it was said 2-3 times, so the copies have to be found in the audio,
    # but only right before a known word and never across another recognised word. 0 disables.
    anchored_dtw_db: float = 2.5
    anchored_lookback: float = 1.5
    silence_margin: float = 0.08  # never cut closer than this to detected speech (s), protects soft word edges
    strain_margin_db: float = 6.0  # level above the noise floor that marks breath/strain noise
    allowed_doubles: set = field(
        default_factory=lambda: {"לאט", "מאוד", "כן", "לא", "עוד", "יותר", "very", "no", "yes", "bye", "ביי"}
    )

    custom: ModeSettings | None = None  # overrides the named mode (used by calibration)

    @property
    def m(self) -> ModeSettings:
        return self.custom or MODES[self.mode]


@dataclass
class Event:
    kind: str  # repetition | prolongation | block | pause | edge
    start: float
    end: float
    cut: tuple[float, float] | None
    source: str  # acoustic | transcript
    note: str = ""

    def as_dict(self):
        return {
            "kind": self.kind,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "cut": [round(self.cut[0], 3), round(self.cut[1], 3)] if self.cut else None,
            "source": self.source,
            "note": self.note,
        }


# --------------------------------------------------------------------------- helpers

_NIQQUD = re.compile(r"[֑-ׇ]")
_PUNCT = re.compile(r"[^\w]", re.UNICODE)


def norm(word: str) -> str:
    return _PUNCT.sub("", _NIQQUD.sub("", word)).lower()


def _profile(f: feat.Features, a: int, b: int) -> np.ndarray:
    """Level-normalised average spectrum of frames [a, b)."""
    p = f.logmel[a:b].mean(axis=0)
    return p - p.mean()


def _chains(items: list, linked) -> list[list]:
    """Group consecutive indices i where linked(i) holds into chains."""
    chains, cur = [], []
    for i in range(len(items)):
        if linked(i):
            cur.append(i)
        elif cur:
            chains.append(cur)
            cur = []
    if cur:
        chains.append(cur)
    return chains


# --------------------------------------------------------------------------- detectors


def acoustic_repetitions(f: feat.Features, regions, cfg: DetectConfig) -> list[Event]:
    """Sound/syllable repetitions ("ב- ב- בית"): short bursts whose spectrum matches the next onset."""
    sec = lambda fr: f.t(fr)  # noqa: E731

    def is_fragment(i: int) -> bool:
        if i + 1 >= len(regions):
            return False
        (s, e), (ns, ne) = regions[i], regions[i + 1]
        if sec(e - s) > cfg.m.fragment_max or sec(ns - e) > cfg.m.fragment_gap_max:
            return False
        n = e - s
        if ne - ns < n:  # the repeat target must be at least as long as the fragment
            return False
        dist = np.mean(np.abs(_profile(f, s, e) - _profile(f, ns, ns + n)))
        return dist < cfg.m.fragment_sim_db

    events = []
    for chain in _chains(regions, is_fragment):
        first, last = chain[0], chain[-1]
        if cfg.m.keep_one_repetition:
            if len(chain) < 2:
                continue
            cut_end = regions[last][0]  # keep the last fragment: "ב- בית"
        else:
            cut_end = regions[last + 1][0]
        a, b = sec(regions[first][0]), sec(cut_end)
        events.append(Event("repetition", a, sec(regions[last + 1][0]), (a, b), "acoustic", f"{len(chain)} fragment(s)"))
    return events


def dtw_distance(a: np.ndarray, b: np.ndarray, min_ratio: float = 0.7) -> float:
    """Open-end DTW between spectral-shape sequences: how well `a` matches the start of `b` (mean dB/band)."""
    a = a - a.mean(axis=1, keepdims=True)
    b = b - b.mean(axis=1, keepdims=True)
    n, m = len(a), len(b)
    cost = np.abs(a[:, None, :] - b[None, :, :]).mean(axis=2)
    d = np.full((n + 1, m + 1), np.inf)
    d[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = cost[i - 1, j - 1] + min(d[i - 1, j], d[i, j - 1], d[i - 1, j - 1])
    lo = max(1, int(min_ratio * n))
    j = np.arange(lo, m + 1)
    return float(np.min(d[n, lo:] / (n + j))) if len(j) else np.inf


def word_repetitions(f: feat.Features, regions, cfg: DetectConfig, cache: dict | None = None) -> list[Event]:
    """Whole-word repetitions ("אני, אני רוצה"): a chunk of speech whose spectral sequence the next chunk repeats."""
    m = cfg.m
    if m.word_dtw_db <= 0:
        return []

    def repeats(i: int) -> bool:
        if i + 1 >= len(regions):
            return False
        (s, e), (ns, ne) = regions[i], regions[i + 1]
        dur = f.t(e - s)
        if not (0.12 <= dur <= m.word_max) or f.t(ns - e) > m.word_gap_max:
            return False
        n = e - s
        if ne - ns < int(0.7 * n):
            return False
        b_end = min(ne, ns + int(1.4 * n))
        key = (s, e, ns, b_end)
        if cache is None or key not in cache:
            dist = dtw_distance(f.logmel[s:e], f.logmel[ns:b_end])
            if cache is None:
                return dist < m.word_dtw_db
            cache[key] = dist
        return cache[key] < m.word_dtw_db

    events = []
    for chain in _chains(regions, repeats):
        first, last = chain[0], chain[-1]
        if m.keep_one_repetition:
            if len(chain) < 2:
                continue
            cut_end = regions[last][0]
        else:
            cut_end = regions[last + 1][0]
        a = f.t(regions[first][0])
        events.append(Event("repetition", a, f.t(regions[last + 1][0]), (a, f.t(cut_end)), "acoustic", f"{len(chain)} word repeat(s)"))
    return events


def prolongations(f: feat.Features, mask: np.ndarray, regions, cfg: DetectConfig) -> list[Event]:
    half = 5
    change = feat.spectral_change(f, half)
    steady = (change < cfg.m.steady_db) & mask
    events = []
    starts = [rs for rs, _ in regions]
    for s, e in runs(steady):
        s, e = max(0, s - half), min(f.n, e + half)  # the change window hides `half` frames each side
        dur = f.t(e - s)
        ri = bisect.bisect_right(starts, s) - 1
        region_end = regions[ri][1] if ri >= 0 and s < regions[ri][1] else e
        phrase_final = f.t(region_end - e) < 0.12
        need = cfg.m.prolong_min * (2.0 if phrase_final else 1.0)  # final lengthening is natural speech
        if dur < need:
            continue
        a, b = f.t(s), f.t(e)
        k = cfg.m.prolong_keep / 2
        events.append(Event("prolongation", a, b, (a + k, b - k), "acoustic", f"{dur:.2f}s steady sound"))
    return events


def transcript_repetitions(words: list[Word], cfg: DetectConfig) -> list[Event]:
    """Word, part-word and phrase repetitions from word timestamps."""
    w = [norm(x.text) for x in words]
    links: dict[int, int] = {}  # i -> index of the word that the copy starting at i repeats
    i = 0
    while i < len(words) - 1:
        if not w[i]:
            i += 1
            continue
        fragment = words[i].text.rstrip().endswith("-") or len(w[i]) == 1
        if fragment and w[i + 1].startswith(w[i]) and w[i] != w[i + 1]:
            links[i] = i + 1
        elif w[i] == w[i + 1] and w[i] not in cfg.allowed_doubles and not w[i].isdigit():
            links[i] = i + 1
        else:
            for n in (3, 2):
                if (i + 2 * n <= len(w) and w[i : i + n] == w[i + n : i + 2 * n] and all(w[i : i + n])
                        and not any(x.isdigit() for x in w[i : i + n])):
                    links[i] = i + n
                    break
        i += 1

    # Chains: copies that lead straight into one another (ש- ש- שלום, אני אני אני).
    events, seen = [], set()
    for i in sorted(links):
        if i in seen:
            continue
        chain = [i]
        while chain[-1] in links and links[chain[-1]] in links and links[chain[-1]] not in seen:
            chain.append(links[chain[-1]])
        seen.update(chain)
        target = links[chain[-1]]
        if cfg.m.keep_one_repetition:
            if len(chain) < 2:
                continue
            cut_to = words[chain[-1]].start
        else:
            cut_to = words[target].start
        a = words[chain[0]].start
        text = " ".join(x.text for x in words[chain[0] : target + 1])
        events.append(Event("repetition", a, words[target].start, (a, cut_to), "transcript", text))
    return events


def transcript_prolongations(words: list[Word], f: feat.Features, mask: np.ndarray, cfg: DetectConfig) -> list[Event]:
    """Held sounds from CTC character timing: a long stretch of continuous speech with no new character.

    Covers "ssss-shalom" before a word's first character and "sha-aaaa-lom" between two characters.
    """
    events = []
    prev_end = 0.0
    for w in words:
        spans = w.chars or []
        stretches = []
        if spans:
            # Before the first character: from where the current stretch of continuous speech began.
            fb = min(f.frame(spans[0][1]), len(mask))
            fa = fb
            while fa > 0 and mask[fa - 1]:
                fa -= 1
            stretches.append((max(prev_end, f.t(fa)), spans[0][1], w.text[:1]))
        stretches += [(a[2], b[1], a[0]) for a, b in zip(spans, spans[1:])]
        for a, b, ch in stretches:
            fa, fb = f.frame(a), f.frame(b)
            if b - a < cfg.m.prolong_min + 0.1 or fb <= fa or not mask[fa:fb].all():
                continue  # short, or a silence/pause in between: not a held sound
            k = cfg.m.prolong_keep / 2
            events.append(Event("prolongation", a, b, (a + 0.05 + k, b - k), "transcript", f"held '{ch}' in '{w.text}'"))
        prev_end = w.end
    return events


def anchored_repetitions(words: list[Word], f: feat.Features, mask: np.ndarray, cfg: DetectConfig) -> list[Event]:
    if cfg.anchored_dtw_db <= 0:
        return []
    regions = runs(mask)
    events = []
    for i, w in enumerate(words):
        lo = max(words[i - 1].end if i else 0.0, w.start - cfg.anchored_lookback)
        chunks = [(max(s, f.frame(lo)), e) for s, e in regions if f.t(e) > lo and f.t(s) < w.end]
        chunks = [(s, e) for s, e in chunks if e - s >= 5]
        if len(chunks) < 2:
            continue
        target = chunks[-1]
        others = [x for j, x in enumerate(words) if j != i]
        copies = []
        for s, e in reversed(chunks[:-1]):
            nxt = copies[0] if copies else target
            if f.t(nxt[0] - e) > 0.8 or f.t(e - s) > 1.0:
                break
            if any(o.start < f.t(e) and o.end + 0.1 > f.t(s) for o in others):
                break  # that chunk is (or touches) another recognised word, never touch it
            n = e - s
            b_end = min(target[1], target[0] + int(1.4 * n) + 1)
            if b_end - target[0] < int(0.7 * n) or dtw_distance(f.logmel[s:e], f.logmel[target[0]:b_end]) >= cfg.anchored_dtw_db:
                break
            copies.insert(0, (s, e))
        if not copies:
            continue
        if cfg.m.keep_one_repetition:
            if len(copies) < 2:
                continue
            cut_to = copies[-1][0]
        else:
            cut_to = target[0]
        a = f.t(copies[0][0])
        events.append(Event("repetition", a, f.t(target[0]), (a, f.t(cut_to)), "transcript",
                            f"{len(copies)} repeat(s) of '{w.text}'"))
    return events


def _sounds_repeated(f: feat.Features, mask: np.ndarray, a: float, b: float, max_db: float) -> bool:
    """Does the speech in [a, b) match the speech that follows b? (the copy we drop vs. the word we keep)"""
    fa, fb = f.frame(a), f.frame(b)
    idx = np.flatnonzero(mask[fa:fb]) + fa
    if len(idx) < 5:
        return True  # nothing audible is removed, only silence
    n = len(idx)
    after = np.flatnonzero(mask[fb : min(f.n, fb + 3 * n + 50)]) + fb
    if len(after) < int(0.7 * n):
        return False
    return dtw_distance(f.logmel[idx], f.logmel[after[: int(1.4 * n) + 1]]) < max_db


def _snap_down(f: feat.Features, t: float, lo: float, hi: float) -> float:
    """Time of the quietest frame in [t+lo, t+hi]: moves a word-based cut point into the dip between sounds."""
    a, b = max(0, f.frame(t + lo)), min(f.n, f.frame(t + hi) + 1)
    if b <= a:
        return t
    return f.t(a + int(np.argmin(f.energy_db[a:b])))


def gaps(f: feat.Features, mask, regions, events, words, cfg: DetectConfig) -> list[Event]:
    """Classify every silence: edge trim, block (compress hard) or natural pause (compress only if long)."""
    out = []
    noise = np.percentile(f.energy_db, 10)
    total = f.t(f.n)
    if regions:
        lead, trail = f.t(regions[0][0]), total - f.t(regions[-1][1])
        if lead > cfg.edge_keep:
            out.append(Event("edge", 0, lead, (0, lead - cfg.edge_keep), "acoustic", "leading silence"))
        if trail > cfg.edge_keep:
            a = f.t(regions[-1][1])
            out.append(Event("edge", a, total, (a + cfg.edge_keep, total), "acoustic", "trailing silence"))

    event_edges = sorted([x.end for x in events] + [x.start for x in events])

    def near_event(t: float) -> bool:
        i = bisect.bisect_left(event_edges, t - 0.1)
        return i < len(event_edges) and event_edges[i] < t + 0.1
    for (ps, pe), (ns, ne) in zip(regions, regions[1:]):
        a, b = f.t(pe), f.t(ns)
        dur = b - a
        if dur < cfg.m.block_min:
            continue
        reasons = []
        strain = np.mean(f.energy_db[pe:ns] > noise + cfg.strain_margin_db)
        if strain > 0.3:
            reasons.append("breath/strain noise")
        if f.t(pe - ps) < 0.15:
            reasons.append("cut-off sound before the gap")
        if near_event(a) or near_event(b):
            reasons.append("next to another stutter event")
        for wd in words or []:
            if wd.start < a - 0.05 and wd.end > b + 0.05:
                reasons.append(f"inside the word '{wd.text}'")
                break
            if abs(wd.end - a) < 0.15 and wd.text.rstrip().endswith("-"):
                reasons.append(f"after the fragment '{wd.text}'")
                break
        if reasons:
            k = max(cfg.m.block_keep / 2, cfg.silence_margin)
            out.append(Event("block", a, b, (a + k, b - k), "acoustic", ", ".join(reasons)))
        elif dur > cfg.m.pause_max:
            k = max(cfg.m.pause_keep / 2, cfg.silence_margin)
            out.append(Event("pause", a, b, (a + k, b - k), "acoustic", "long pause shortened"))
    return out


def detect(x: np.ndarray, sr: int, mask: np.ndarray, f: feat.Features, words: list[Word] | None, cfg: DetectConfig):
    regions = runs(mask)
    acoustic = acoustic_repetitions(f, regions, cfg) + word_repetitions(f, regions, cfg) + prolongations(f, mask, regions, cfg)
    events = list(acoustic) if cfg.acoustic_speech_cuts else []
    if words:
        # Grounded in recognised words, so safe to cut. CTC character times are spikes, not onsets: snap each
        # cut edge to the quietest point just before the word it sits on.
        for e in transcript_repetitions(words, cfg):
            a = _snap_down(f, e.cut[0], -0.15, 0.0)
            b = _snap_down(f, e.cut[1], -0.25, -0.01)
            if cfg.verify_repetition_db > 0 and not _sounds_repeated(f, mask, a, b, cfg.verify_repetition_db):
                continue
            events.append(replace(e, cut=(a, max(a, b))))
        for e in anchored_repetitions(words, f, mask, cfg):
            if not any(x.kind == "repetition" and x.cut[0] < e.cut[1] and e.cut[0] < x.cut[1] for x in events):
                events.append(e)
        events += transcript_prolongations(words, f, mask, cfg)
    events += gaps(f, mask, regions, acoustic + events, words, cfg)
    events.sort(key=lambda e: e.start)
    return events
