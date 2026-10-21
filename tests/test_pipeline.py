import numpy as np
import pytest

from fluency import Settings, process
from fluency.detect import DetectConfig, transcript_repetitions
from fluency.edit import apply_cuts
from fluency.transcribe import Word

from synth import SR, W1, W2, W3, fricative, join, silence, syllable, vowel

GAP = 0.09  # normal gap between words


def kinds(res):
    return [e.kind for e in res.events if e.kind != "edge"]


def fluent():
    return join(silence(0.2), W1(), silence(GAP), W2(), silence(GAP), W3(), silence(0.2))


@pytest.mark.parametrize("mode", ["gentle", "full", "strong"])
def test_fluent_speech_is_left_alone(mode):
    x = fluent()
    res = process(x, SR, Settings(mode=mode, vad="energy"))
    assert kinds(res) == []
    assert abs(len(res.audio) - len(x)) / SR < 0.02


def test_natural_short_pause_is_kept():
    x = join(silence(0.2), W1(), silence(GAP), W2(), silence(0.8), W3(), silence(0.2))
    res = process(x, SR, Settings(mode="gentle", vad="energy"))
    assert kinds(res) == []


def test_long_pause_is_shortened():
    x = join(silence(0.2), W1(), silence(GAP), W2(), silence(2.5), W3(), silence(0.2))
    res = process(x, SR, Settings(mode="gentle", vad="energy"))
    assert kinds(res) == ["pause"]
    assert len(x) / SR - len(res.audio) / SR > 1.4


def test_fricative_prolongation_is_shortened():
    # "ssssss-amir": a 0.9 s held fricative before the word
    x = join(silence(0.2), W1(), silence(GAP), fricative(0.9, (4000, 7000)), W2(), silence(0.2))
    res = process(x, SR, Settings(mode="full", vad="energy"))
    assert "prolongation" in kinds(res)
    removed = len(x) / SR - len(res.audio) / SR
    assert 0.6 < removed < 0.9


def test_vowel_prolongation_is_shortened():
    x = join(silence(0.2), W1(), silence(GAP), vowel("a", 1.0, f0=(130, 130)), W3(), silence(0.2))
    res = process(x, SR, Settings(mode="full", vad="energy"))
    assert "prolongation" in kinds(res)


def test_block_with_strain_noise_is_compressed():
    # mid-phrase gap filled with audible breath/strain noise, ~30 dB under speech
    strain = 0.0015 * np.random.default_rng(1).standard_normal(int(1.2 * SR)).astype(np.float32)
    x = join(silence(0.2), W1(), silence(GAP), strain, W2(), silence(0.2))
    res = process(x, SR, Settings(mode="full", vad="energy"))
    assert "block" in kinds(res)
    assert len(x) / SR - len(res.audio) / SR > 0.9


def test_sound_repetition_is_merged():
    # "ba- ba- ba- bano": short fragments repeating the onset of the next word
    frag = lambda: syllable((1000, 2500), "o", dur=0.12)  # noqa: E731
    x = join(silence(0.2), W1(), silence(GAP), frag(), silence(0.18), frag(), silence(0.18), frag(), silence(0.18),
             W2(), silence(0.2))
    full = process(x, SR, Settings(mode="full", vad="energy"))
    assert "repetition" in kinds(full)
    assert len(x) / SR - len(full.audio) / SR > 0.85
    gentle = process(x, SR, Settings(mode="gentle", vad="energy"))
    assert "repetition" in kinds(gentle)
    assert len(gentle.audio) > len(full.audio)  # gentle leaves one repetition


def test_transcript_repetitions():
    def w(text, s):
        return Word(text, s, s + 0.2)

    words = [w("אני", 0.0), w("אני", 0.3), w("אני", 0.6), w("ר-", 0.9), w("רוצה", 1.2), w("לאט", 1.5), w("לאט", 1.8)]
    full = transcript_repetitions(words, DetectConfig(mode="full"))
    assert [e.cut for e in full] == [(0.0, 0.6), (0.9, 1.2)]  # "לאט לאט" is a real doubling, kept
    gentle = transcript_repetitions(words, DetectConfig(mode="gentle"))
    assert [e.cut for e in gentle] == [(0.0, 0.3)]

    phrase = [w("אני", 0.0), w("רוצה", 0.3), w("אני", 0.6), w("רוצה", 0.9), w("ללכת", 1.2)]
    assert [e.cut for e in transcript_repetitions(phrase, DetectConfig(mode="full"))] == [(0.0, 0.6)]


def test_crossfade_has_no_clicks():
    t = np.arange(SR) / SR
    x = (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    out, joins = apply_cuts(x, SR, [(0.3013, 0.5507)])
    assert len(joins) == 1
    assert np.max(np.abs(np.diff(out))) < 0.05  # a hard splice of a 200 Hz sine would jump up to 0.6


def test_silence_input():
    x = np.zeros(SR, dtype=np.float32)
    res = process(x, SR)
    assert res.events == [] and len(res.audio) == SR


def test_pipeline_uses_transcript_for_word_repetitions():
    # "W1 W1 W2": the whole word is repeated, which the acoustic detectors do not catch on their own
    x = join(silence(0.2), W1(), silence(GAP), W1(), silence(GAP), W2(), silence(0.2))
    d = len(W1()) / SR
    s2 = 0.2 + d + GAP
    words = [Word("אני", 0.2, 0.2 + d), Word("אני", s2, s2 + d), Word("רוצה", s2 + d + GAP, s2 + 2 * d + GAP)]
    res = process(x, SR, Settings(mode="full", vad="energy"), transcriber=lambda *_: words)
    assert "repetition" in kinds(res)
    assert abs((len(x) - len(res.audio)) / SR - (d + GAP)) < 0.05
