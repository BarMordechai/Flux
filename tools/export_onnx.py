"""Export the Hebrew CTC model to an int8 ONNX file + vocab for the Android app.

    python tools/export_onnx.py --out android/app/src/main/assets
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fluency.ctc import DEFAULT_MODEL  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    proc = Wav2Vec2Processor.from_pretrained(a.model)
    model = Wav2Vec2ForCTC.from_pretrained(a.model).eval()
    fp32 = out / "ctc-fp32.onnx"
    torch.onnx.export(
        model,
        torch.zeros(1, 16000),
        str(fp32),
        input_names=["input_values"],
        output_names=["logits"],
        dynamic_axes={"input_values": {1: "samples"}, "logits": {1: "frames"}},
        opset_version=17,
        dynamo=False,
    )
    quantize_dynamic(str(fp32), str(out / "ctc.onnx"), weight_type=QuantType.QUInt8)
    fp32.unlink()
    for extra in out.glob("ctc-fp32.onnx*"):
        extra.unlink()

    vocab = proc.tokenizer.get_vocab()
    meta = {
        "vocab": [t for t, _ in sorted(vocab.items(), key=lambda kv: kv[1])],
        "blank": proc.tokenizer.pad_token_id,
        "delimiter": getattr(proc.tokenizer, "word_delimiter_token", "|") or "|",
        "normalize": bool(getattr(proc.feature_extractor, "do_normalize", True)),
        "model": a.model,
    }
    (out / "ctc.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(f"wrote {out / 'ctc.onnx'} ({(out / 'ctc.onnx').stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
