"""Stutter event detection: repetitions, prolongations and blocks.

Every detector returns Events that carry the interval to remove (`cut`). Detection is deliberately
conservative: cutting fluent speech is far worse for the user than leaving a stutter in.
"""

import re
from dataclasses import dataclass, field

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


MODES = {
    "gentle": ModeSettings(0.45, 0.20, 0.35, 0.25, 1.6, 0.9, True),
    "full": ModeSettings(0.30, 0.12, 0.25, 0.12, 1.0, 0.55, False),
}


@dataclass
class DetectConfig:
    mode: str = "gentle"
    edge_keep: float = 0.25  # silence kept at the start/end of the message (s)
    fragment_max: float = 0.35  # a burst shorter than this can be a part-word repetition (s)
    fragment_gap_max: float = 0.6  # longest gap between a fragment and its repeat (s)
    fragment_sim_db: float = 4.0  # spectral distance below which a fragment matches the next onset
    steady_db: float = 2.2  # spectral change below which a frame counts as a steady sound (calibrate on real data)
    strain_margin_db: float = 6.0  # level above the noise floor that marks breath/strain noise
    allowed_doubles: set = field(
        default_factory=lambda: {"לאט", "מאוד", "כן", "לא", "עוד", "יותר", "very", "no", "yes", "bye", "ביי"}
    )

    @property
    def m(self) -> ModeSettings:
        return MODES[self.mode]


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
        if sec(e - s) > cfg.fragment_max or sec(ns - e) > cfg.fragment_gap_max:
            return False
        n = e - s
        if ne - ns < n:  # the repeat target must be at least as long as the fragment
            return False
        dist = np.mean(np.abs(_profile(f, s, e) - _profile(f, ns, ns + n)))
        return dist < cfg.fragment_sim_db

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


def prolongations(f: feat.Features, mask: np.ndarray, regions, cfg: DetectConfig) -> list[Event]:
    half = 5
    change = feat.spectral_change(f, half)
    steady = (change < cfg.steady_db) & mask
    events = []
    for s, e in runs(steady):
        s, e = max(0, s - half), min(f.n, e + half)  # the change window hides `half` frames each side
        dur = f.t(e - s)
        region_end = next((re_ for rs, re_ in regions if rs <= s < re_), e)
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
        elif w[i] == w[i + 1] and w[i] not in cfg.allowed_doubles:
            links[i] = i + 1
        else:
            for n in (3, 2):
                if i + 2 * n <= len(w) and w[i : i + n] == w[i + n : i + 2 * n] and all(w[i : i + n]):
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

    event_edges = [x.end for x in events] + [x.start for x in events]
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
        if any(abs(t - a) < 0.1 or abs(t - b) < 0.1 for t in event_edges):
            reasons.append("next to another stutter event")
        for wd in words or []:
            if wd.start < a - 0.05 and wd.end > b + 0.05:
                reasons.append(f"inside the word '{wd.text}'")
                break
            if abs(wd.end - a) < 0.15 and wd.text.rstrip().endswith("-"):
                reasons.append(f"after the fragment '{wd.text}'")
                break
        if reasons:
            k = cfg.m.block_keep / 2
            out.append(Event("block", a, b, (a + k, b - k), "acoustic", ", ".join(reasons)))
        elif dur > cfg.m.pause_max:
            k = cfg.m.pause_keep / 2
            out.append(Event("pause", a, b, (a + k, b - k), "acoustic", "long pause shortened"))
    return out


def detect(x: np.ndarray, sr: int, mask: np.ndarray, f: feat.Features, words: list[Word] | None, cfg: DetectConfig):
    regions = runs(mask)
    events = acoustic_repetitions(f, regions, cfg)
    events += prolongations(f, mask, regions, cfg)
    if words:
        events += transcript_repetitions(words, cfg)
    events += gaps(f, mask, regions, events, words, cfg)
    events.sort(key=lambda e: e.start)
    return events
