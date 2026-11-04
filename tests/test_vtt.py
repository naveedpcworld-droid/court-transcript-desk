from pipeline.transcripts import parse_vtt, dedupe_rolling


def test_parse_vtt_basic():
    raw = """WEBVTT

00:00:01.000 --> 00:00:04.000
Hello court.

00:00:04.000 --> 00:00:07.500
Good morning.
"""
    segs = parse_vtt(raw)
    assert len(segs) == 2
    assert segs[0]["start"] == 1.0
    assert segs[0]["text"] == "Hello court."
    assert segs[1]["end"] == 7.5


def test_rolling_captions_collapse():
    segs = [
        {"start": 1, "end": 2, "text": "I am"},
        {"start": 2, "end": 3, "text": "I am a living man"},
        {"start": 3, "end": 4, "text": "I am a living man"},
    ]
    out = dedupe_rolling(segs)
    assert len(out) == 1
    assert out[0]["text"] == "I am a living man"
