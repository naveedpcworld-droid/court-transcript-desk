from pipeline.classify import classify_video, extract_judge


def test_sovereign_and_judge():
    r = classify_video(
        title="Judge Boyd SHUTS DOWN Sovereign Citizen",
        description="",
        transcript_text="I am a living man. The court has no jurisdiction. " * 30,
        default_judge="Judge Stephanie Boyd",
        default_court="187th District Court",
    )
    assert "sovereign_citizen" in r["topics"]
    assert r["judge"]
    assert r["confidence"] > 0.6


def test_extract_judge_stops_verb():
    assert extract_judge("Judge Boyd DESTROYS defendant") == "Boyd"
