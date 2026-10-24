"""Word-guided editing on Hebrew: real fluent speech (Google FLEURS he_il) with stutters inserted at known spots.

Because we insert the stutters ourselves, every removed sample can be checked: removing inserted audio is a
hit, removing original speech is the error that must never happen.

    python tools/eval_hebrew_synthetic.py --n 80 --out report
"""

import argparse
import csv
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fluency import Settings, audio_io, features as feat, process  # noqa: E402
from fluency.ctc import CtcTranscriber  # noqa: E402
from fluency.edit import merge  # noqa: E402
from fluency.vad import energy_vad  # noqa: E402

SR = 16000
FLEURS = "https://huggingface.co/datasets/google/fleurs/resolve/main/data/he_il/"
KINDS = ["word_rep", "sound_rep", "prolongation", "block"]
rng = np.random.default_rng(0)


def fetch(url):
    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


def load_fleurs(n):
    rows = list(csv.reader(io.StringIO(fetch(FLEURS + "test.tsv").decode()), delimiter="\t", quoting=csv.QUOTE_NONE))
    want = {r[1]: r[2] for r in rows[: n * 2]}
    out = []
    with tarfile.open(fileobj=io.BytesIO(fetch(FLEURS + "audio/test.tar.gz"))) as tar:
        for m in tar:
            name = m.name.rsplit("/", 1)[-1]
            if name in want and len(out) < n:
                out.append((name, want[name], audio_io.decode(tar.extractfile(m).read())))
    return out


def dip_before(x, t, lo=0.2):
    """Sample index of the quietest 10 ms in the `lo` seconds before time t (the gap before a word)."""
    a, b = max(0, int((t - lo) * SR)), max(1, int(t * SR))
    env = np.convolve(np.abs(x[a:b]), np.ones(160) / 160, mode="same")
    return a + int(np.argmin(env)) if len(env) else b


def grain_hold(x, at, dur):
    """A held sound: overlap-add 40 ms grains taken just after `at` (sample index) for `dur` seconds."""
    g = x[at : at + 640] * np.hanning(640)
    out = np.zeros(int(dur * SR) + 640)
    for s in range(0, int(dur * SR), 320):
        out[s : s + 640] += g
    return out[: int(dur * SR)].astype(np.float32)


def insert_stutters(x, words, k):
    """Insert `k` stutters before random words. Returns (audio, inserted-sample mask, [(kind, word)])."""
    cand = [i for i, w in enumerate(words) if i > 0 and w.end - w.start > 0.2]
    picks = sorted(rng.choice(cand, size=min(k, len(cand)), replace=False)) if cand else []
    parts, mask, labels, pos = [], [], [], 0
    level = np.sqrt(np.mean(x**2)) + 1e-6
    for i in picks:
        w = words[i]
        p = dip_before(x, w.start)
        kind = KINDS[rng.integers(len(KINDS))]
        on = p  # word onset (the dip just before its first character)
        if kind == "word_rep":
            ins = np.concatenate([x[on : int(w.end * SR) + 320], np.zeros(int(0.15 * SR), np.float32)])
        elif kind == "sound_rep":
            frag = np.concatenate([x[on : on + int(0.14 * SR)], np.zeros(int(0.12 * SR), np.float32)])
            ins = np.concatenate([frag, frag])
        elif kind == "prolongation":
            ins = grain_hold(x, on + 160, 0.6)
        else:
            ins = (level * 0.03 * rng.standard_normal(int(0.9 * SR))).astype(np.float32)
        parts += [x[pos:p], ins]
        mask += [np.zeros(p - pos, bool), np.ones(len(ins), bool)]
        labels.append((kind, w.text))
        pos = p
    parts.append(x[pos:])
    mask.append(np.zeros(len(x) - pos, bool))
    return np.concatenate(parts).astype(np.float32), np.concatenate(mask), labels


def removed_mask(n, events):
    m = np.zeros(n, bool)
    for a, b in merge([e.cut for e in events if e.cut]):
        m[int(a * SR) : int(b * SR)] = True
    return m


def speech_mask(y):
    f = feat.compute(y, SR)
    frames = energy_vad(f)
    return np.repeat(frames, f.hop)[: len(y)] if len(frames) else np.zeros(len(y), bool)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--out", default="report")
    ap.add_argument("--asr", default="ctc", help="ctc | whisper:<faster-whisper model id>")
    a = ap.parse_args()
    out = Path(a.out)
    (out / "examples").mkdir(parents=True, exist_ok=True)

    ctc = CtcTranscriber()  # positions the inserted stutters
    if a.asr.startswith("whisper:"):
        from fluency.transcribe import Transcriber

        asr = Transcriber(a.asr[8:], device="cpu", compute_type="int8")
    else:
        asr = ctc
    data = load_fleurs(a.n)
    print(f"loaded {len(data)} FLEURS utterances", flush=True)
    stats = {m: {"inserted": {k: 0.0 for k in KINDS}, "removed": {k: 0.0 for k in KINDS},
                 "real_cut_s": [], "clean_real_cut_s": []} for m in ("gentle", "full", "strong")}
    examples = []
    for idx, (name, text, x) in enumerate(data):
        words = ctc(x, SR)
        y, ins, labels = insert_stutters(x, words, k=2)
        # Which inserted samples belong to which kind, in order of insertion.
        runs_ = np.flatnonzero(np.diff(np.concatenate([[0], ins.astype(int), [0]])))
        spans = list(zip(runs_[::2], runs_[1::2]))
        y_words = asr(y, SR)
        sp_y, sp_x = speech_mask(y), speech_mask(x)
        clean_words = asr(x, SR) if asr is not ctc else words
        for mode in stats:
            res = process(y, SR, Settings(mode=mode, vad="energy"), transcriber=lambda *_: y_words)
            rem = removed_mask(len(y), res.events)
            for (kind, _), (s, e) in zip(labels, spans):
                stats[mode]["inserted"][kind] += (e - s) / SR
                stats[mode]["removed"][kind] += rem[s:e].sum() / SR
            stats[mode]["real_cut_s"].append(float((rem & ~ins & sp_y).sum() / SR))
            clean = process(x, SR, Settings(mode=mode, vad="energy"), transcriber=lambda *_: clean_words)
            stats[mode]["clean_real_cut_s"].append(float((removed_mask(len(x), clean.events) & sp_x).sum() / SR))
            if mode == "full" and len(examples) < 8:
                stem = f"{len(examples) + 1:02d}"
                audio_io.save(str(out / "examples" / f"{stem}-before.ogg"), y)
                audio_io.save(str(out / "examples" / f"{stem}-after.ogg"), res.audio)
                examples.append({"file": stem, "inserted": labels, "heard": " ".join(w.text for w in y_words),
                                 "text": text, "real_speech_cut_s": stats[mode]["real_cut_s"][-1],
                                 "events": [e.as_dict() for e in res.events if e.kind != "edge"]})
        print(f"{idx + 1}/{len(data)} {labels} real-cut(full)={stats['full']['real_cut_s'][-1]:.3f}s", flush=True)

    lines = ["# Hebrew word-guided editing (FLEURS he_il + inserted stutters)", "",
             f"{len(data)} utterances, 2 stutters inserted in each. Recogniser: {a.asr}.", "",
             "| mode | " + " | ".join(f"{k} removed" for k in KINDS)
             + " | real speech cut (stuttered input) | utterances with >50 ms real speech cut | real speech cut (fluent input) |",
             "|---|" + "---|" * (len(KINDS) + 3)]
    for mode, s in stats.items():
        rec = [s["removed"][k] / s["inserted"][k] if s["inserted"][k] else 0 for k in KINDS]
        rc = np.array(s["real_cut_s"])
        cc = np.array(s["clean_real_cut_s"])
        lines.append(f"| {mode} | " + " | ".join(f"{r:.0%}" for r in rec)
                     + f" | {rc.sum():.2f}s total | {np.mean(rc > 0.05):.0%} | {cc.sum():.2f}s total |")
    lines += ["", "## Examples (examples/NN-before.ogg / NN-after.ogg, full mode)", ""]
    for ex in examples:
        lines += [f"**{ex['file']}** inserted {ex['inserted']}, real speech cut {ex['real_speech_cut_s']:.3f}s",
                  f"- text: {ex['text']}", f"- heard: {ex['heard']}",
                  "- edits: " + "; ".join(f"{e['kind']} {e['start']}-{e['end']} ({e['note']})" for e in ex["events"]), ""]
    (out / "summary.md").write_text("\n".join(lines))
    (out / "results.json").write_text(json.dumps({"stats": stats, "examples": examples}, ensure_ascii=False, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
