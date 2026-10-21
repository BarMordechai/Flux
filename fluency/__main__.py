"""Command line: python -m fluency in.opus out.ogg [--mode full] [--whisper small]"""

import argparse
import json
import sys

from . import audio_io
from .enroll import build_profile
from .pipeline import Settings, process
from .transcribe import load_transcriber


def main(argv=None):
    p = argparse.ArgumentParser(prog="fluency", description="Smooth stuttering in a recorded voice message.")
    p.add_argument("input", help="any audio file: .opus/.ogg (WhatsApp), .m4a, .wav, .mp3 ...")
    p.add_argument("output", help="output file; .ogg gives a WhatsApp-style Opus voice note")
    p.add_argument("--mode", choices=["gentle", "full"], default="gentle")
    p.add_argument("--language", default="he")
    p.add_argument("--whisper", default="none", help="faster-whisper model, e.g. small, large-v3, or an ivrit.ai ct2 model")
    p.add_argument("--vad", choices=["auto", "silero", "energy"], default="auto")
    p.add_argument("--report", help="write a JSON report of the detected events here")
    p.add_argument("--enroll", action="store_true", help="instead of smoothing, save the most fluent 12 s as a voice reference")
    a = p.parse_args(argv)

    x = audio_io.load(a.input)
    if a.enroll:
        prof = build_profile(x, audio_io.SR)
        audio_io.save(a.output, prof.reference, prof.sr)
        print(f"voice reference saved to {a.output} ({len(prof.reference) / prof.sr:.1f}s)")
        return 0

    tr = load_transcriber(a.whisper)
    if a.whisper != "none" and tr is None:
        print("faster-whisper is not installed; continuing with acoustic detection only", file=sys.stderr)
    res = process(x, audio_io.SR, Settings(mode=a.mode, language=a.language, vad=a.vad), transcriber=tr)
    audio_io.save(a.output, res.audio, res.sr)
    rep = res.report(len(x) / audio_io.SR)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"{rep['original_seconds']}s -> {rep['output_seconds']}s  {rep['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
