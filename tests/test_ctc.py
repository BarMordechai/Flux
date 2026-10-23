import numpy as np

from fluency.ctc import FRAME, decode_words


def logits_for(frames, vocab):
    out = np.zeros((len(frames), len(vocab)))
    for t, tok in enumerate(frames):
        out[t, vocab.index(tok)] = 1.0
    return out


def test_decode_words_keeps_repetitions_and_times():
    vocab = ["<pad>", "|", "א", "נ", "י"]
    frames = ["<pad>", "א", "נ", "נ", "י", "|", "<pad>", "א", "<pad>", "נ", "י", "<pad>"]
    words = decode_words(logits_for(frames, vocab), vocab, blank=0)
    assert [w.text for w in words] == ["אני", "אני"]  # verbatim: the repetition is kept
    assert words[0].start == 1 * FRAME and abs(words[0].end - 5 * FRAME) < 1e-9
    assert words[0].chars[1] == ("נ", 2 * FRAME, 4 * FRAME)  # a held character spans its frames
    assert words[1].start == 7 * FRAME
