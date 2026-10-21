"""Calibrate the acoustic detectors on SEP-28k (Apple's Stuttering Events in Podcasts dataset).

SEP-28k labels 3-second podcast clips (3 annotators each) with Prolongation, Block, SoundRep, WordRep, etc.
The audio is not redistributed: this script downloads episodes from the podcasts' own URLs, runs the
detectors over each whole episode, and scores them clip by clip. Nothing is saved except the report.

    python tools/calibrate_sep28k.py --episodes 40 --out report

Writes report/summary.md (human readable) and report/results.json (all grid points).
"""

import argparse
import csv
import io
import itertools
import json
import random
import subprocess
import sys
import urllib.request
from collections import defaultdict
from dataclasses import fields, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fluency import features as feat  # noqa: E402
from fluency.detect import MODES, DetectConfig, acoustic_repetitions, detect, gaps, prolongations  # noqa: E402
from fluency.vad import energy_vad, runs  # noqa: E402

BASE = "https://raw.githubusercontent.com/apple/ml-stuttering-events-dataset/main/"
SR = 16000
CLASSES = ["Prolongation", "Block", "SoundRep", "WordRep", "Interjection"]
DETECTS = {"prolongation": ["Prolongation"], "block": ["Block"], "repetition": ["SoundRep", "WordRep"]}

# Parameter grids, one per detector (each detector only reads its own parameters).
GRID = {
    "prolongation": {"steady_db": [1.6, 2.2, 2.8, 3.4, 4.0], "prolong_min": [0.18, 0.22, 0.30, 0.45]},
    "repetition": {
        "fragment_sim_db": [3.0, 4.0, 5.5, 7.0],
        "fragment_max": [0.25, 0.35, 0.45, 0.6],
        "fragment_gap_max": [0.4, 0.6, 0.8, 1.0],
    },
    "block": {"block_min": [0.12, 0.18, 0.25, 0.35], "strain_margin_db": [3.0, 4.5, 6.0, 8.0]},
}


def fetch_csv(name):
    with urllib.request.urlopen(BASE + name, timeout=60) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8")), skipinitialspace=True))


def load_url(url):
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-rw_timeout", "30000000", "-i", url,
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
        capture_output=True, timeout=900,
    )
    if p.returncode != 0 or len(p.stdout) < SR * 4 * 60:
        return None
    return np.frombuffer(p.stdout, dtype=np.float32)


def clip_labels(rows):
    """{(show, ep): [(start_s, stop_s, {class: votes})]} for clean, speech-only clips."""
    head = rows[0]
    idx = {h: i for i, h in enumerate(head)}
    out = defaultdict(list)
    for r in rows[1:]:
        if len(r) < len(head):
            continue
        v = {h: int(r[idx[h]]) for h in head[5:]}
        if v["PoorAudioQuality"] or v["Music"] or v["NoSpeech"] or v["Unsure"]:
            continue
        out[(r[0], r[1])].append((int(r[3]) / SR, int(r[4]) / SR, v))
    return out


MODE_FIELDS = {f.name for f in fields(MODES["full"])}


def detect_kind(kind, f, mask, regions, params):
    mode = replace(MODES["full"], **{k: v for k, v in params.items() if k in MODE_FIELDS})
    cfg = DetectConfig(mode="full", custom=mode, **{k: v for k, v in params.items() if k not in MODE_FIELDS})
    if kind == "prolongation":
        return prolongations(f, mask, regions, cfg)
    if kind == "repetition":
        return acoustic_repetitions(f, regions, cfg)
    reps = acoustic_repetitions(f, regions, cfg) + prolongations(f, mask, regions, cfg)
    return [e for e in gaps(f, mask, regions, reps, None, cfg) if e.kind == "block"]


def score(events, clips):
    """Per clip: did any event overlap it?"""
    starts = np.array(sorted(e.start for e in events))
    ends = np.array([e.end for e in sorted(events, key=lambda e: e.start)])
    hits = []
    for a, b, _ in clips:
        i = np.searchsorted(starts, b)
        hits.append(bool(i and np.any(ends[:i] > a)))
    return hits


def _fmt(v):
    return "-" if v is None else f"{v:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="report")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    episodes = fetch_csv("SEP-28k_episodes.csv")
    labels = clip_labels(fetch_csv("SEP-28k_labels.csv"))
    by_show = defaultdict(list)
    for r in episodes:
        if len(r) >= 5 and (r[3], r[4]) in labels:
            by_show[r[3]].append((r[3], r[4], r[2]))
    rng = random.Random(a.seed)
    for v in by_show.values():
        rng.shuffle(v)
    queue = [ep for group in itertools.zip_longest(*by_show.values()) for ep in group if ep]  # round-robin over shows

    # Per detector & grid point: per clip hit list, concatenated over episodes.
    hits = defaultdict(list)
    all_clips = []
    used = []
    for show, ep, url in queue:
        if len(used) >= a.episodes:
            break
        x = load_url(url)
        if x is None:
            print(f"skip {show}/{ep} (download failed)", flush=True)
            continue
        clips = labels[(show, ep)]
        f = feat.compute(x, SR)
        mask = energy_vad(f)
        regions = runs(mask)
        for kind, grid in GRID.items():
            keys = list(grid)
            for values in itertools.product(*grid.values()):
                params = dict(zip(keys, values))
                hits[(kind, json.dumps(params, sort_keys=True))] += score(detect_kind(kind, f, mask, regions, params), clips)
        for m in MODES:
            evs = [e for e in detect(x, SR, mask, f, None, DetectConfig(mode=m)) if e.kind not in ("edge", "pause")]
            hits[("mode:" + m, "any")] += score(evs, clips)
            for kind in DETECTS:
                hits[("mode:" + m, kind)] += score([e for e in evs if e.kind == kind], clips)
        all_clips += clips
        used.append(f"{show}/{ep}")
        print(f"done {len(used)}/{a.episodes}: {show}/{ep} ({len(clips)} clips, {len(x) / SR / 60:.0f} min)", flush=True)

    pos = {c: np.array([v[c] >= 2 for _, _, v in all_clips]) for c in CLASSES}
    fluent = np.array([v["NoStutteredWords"] >= 2 and all(v[c] == 0 for c in CLASSES) for _, _, v in all_clips])
    results = []
    mode_rows = []
    for m in MODES:
        h_any = np.array(hits[("mode:" + m, "any")])
        row = {"mode": m, "false_positive_rate": float(h_any[fluent].mean()) if fluent.any() else None}
        for kind, cls in DETECTS.items():
            h = np.array(hits[("mode:" + m, kind)])
            for c in cls:
                row[f"recall_{c}"] = float(h[pos[c]].mean()) if pos[c].any() else None
        row["recall_any_stutter"] = float(h_any[np.any([pos[c] for c in CLASSES[:4]], axis=0)].mean())
        mode_rows.append(row)
    for (kind, params), h in hits.items():
        if kind.startswith("mode:"):
            continue
        h = np.array(h)
        row = {"detector": kind, "params": json.loads(params), "false_positive_rate": float(h[fluent].mean())}
        for c in CLASSES:
            row[f"recall_{c}"] = float(h[pos[c]].mean()) if pos[c].any() else None
        rs = [row[f"recall_{c}"] for c in DETECTS[kind] if row[f"recall_{c}"] is not None]
        row["recall"] = float(np.mean(rs)) if rs else 0.0
        results.append(row)

    (out / "results.json").write_text(json.dumps(
        {"episodes": used, "clips": len(all_clips), "fluent_clips": int(fluent.sum()),
         "positives": {c: int(p.sum()) for c, p in pos.items()}, "modes": mode_rows, "results": results}, indent=1))

    lines = [f"# SEP-28k calibration", "", f"{len(used)} episodes, {len(all_clips)} clips, {int(fluent.sum())} fluent clips.",
             "Positives: " + ", ".join(f"{c} {int(p.sum())}" for c, p in pos.items()), "",
             "## Current modes", "",
             "| mode | FP on fluent clips | any stutter | Prolongation | Block | SoundRep | WordRep |", "|---|---|---|---|---|---|---|"]
    for r in mode_rows:
        lines.append(f"| {r['mode']} | {_fmt(r['false_positive_rate'])} | {_fmt(r['recall_any_stutter'])} | "
                     + " | ".join(_fmt(r[f"recall_{c}"]) for c in ["Prolongation", "Block", "SoundRep", "WordRep"]) + " |")
    lines.append("")
    base = DetectConfig(mode="full")
    current = {k: {p: getattr(MODES["full"], p, getattr(base, p, None)) for p in GRID[k]} for k in GRID}
    for kind in GRID:
        rows = sorted((r for r in results if r["detector"] == kind), key=lambda r: r["false_positive_rate"])
        lines += [f"## {kind}", "", f"Current (full mode): {current[kind]}", "",
                  "| FP rate on fluent clips | recall | " + " | ".join(DETECTS[kind]) + " | params |",
                  "|---|---|" + "---|" * len(DETECTS[kind]) + "---|"]
        # Pareto frontier: best recall at each false-positive level.
        best = -1
        for r in rows:
            if r["recall"] > best:
                best = r["recall"]
                lines.append(f"| {r['false_positive_rate']:.3f} | {r['recall']:.3f} | "
                             + " | ".join(_fmt(r[f"recall_{c}"]) for c in DETECTS[kind]) + f" | {r['params']} |")
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
