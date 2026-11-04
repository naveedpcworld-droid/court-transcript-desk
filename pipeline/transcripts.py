"""Caption acquisition and VTT normalisation."""
from __future__ import annotations

import glob
import html
import os
import re
import shutil
import tempfile
from typing import Any

from .utils import normalize_space, run_cmd

VTT_TIME = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?[.,](\d{3})")


def vtt_seconds(value: str) -> float:
    m = VTT_TIME.search(value)
    if not m:
        return 0.0
    a, b, c, ms = m.groups()
    if c is None:
        return int(a) * 60 + int(b) + int(ms) / 1000
    return int(a) * 3600 + int(b) * 60 + int(c) + int(ms) / 1000


def clean_caption_text(lines: list[str]) -> str:
    text = " ".join(lines)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\{\\[^}]+\}", " ", text)
    text = text.replace("&nbsp;", " ")
    return normalize_space(text)


def parse_vtt(raw: str) -> list[dict[str, Any]]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n{2,}", raw)
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines or lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        time_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if time_idx is None:
            continue
        start_raw, end_raw = lines[time_idx].split("-->", 1)
        start = vtt_seconds(start_raw)
        end = vtt_seconds(end_raw)
        text = clean_caption_text(lines[time_idx + 1:])
        if not text or text.lower() in {"[music]", "music"}:
            continue
        segments.append({"start": round(start, 2), "end": round(max(end, start + 0.4), 2), "text": text})
    return dedupe_rolling(segments)


def dedupe_rolling(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse YouTube auto-caption rolling repeats."""
    out: list[dict[str, Any]] = []
    for seg in segments:
        text = normalize_space(seg["text"])
        if not text:
            continue
        if out:
            prev = out[-1]
            p = prev["text"].lower()
            t = text.lower()
            if t == p:
                prev["end"] = max(prev["end"], seg["end"])
                continue
            if t.startswith(p + " ") and len(text) > len(prev["text"]):
                prev["text"] = text
                prev["end"] = max(prev["end"], seg["end"])
                continue
            if p.startswith(t + " ") and len(prev["text"]) > len(text):
                prev["end"] = max(prev["end"], seg["end"])
                continue
        out.append({"start": seg["start"], "end": seg["end"], "text": text})
    return out


def _from_ytdlp(url: str, video_id: str, languages: list[str], timeout: int = 120) -> list[dict[str, Any]]:
    tmp = tempfile.mkdtemp(prefix="cts-")
    try:
        lang_arg = ",".join(["en.*", "en"] + languages)
        cmd = [
            "yt-dlp", "--no-warnings", "--no-playlist", "--skip-download",
            "--write-subs", "--write-auto-subs",
            "--sub-langs", lang_arg, "--sub-format", "vtt", "--convert-subs", "vtt",
            "-o", os.path.join(tmp, "%(id)s.%(ext)s"), url,
        ]
        code, _stdout, stderr = run_cmd(cmd, timeout=timeout)
        files = sorted(glob.glob(os.path.join(tmp, f"{video_id}*.vtt")))
        if not files:
            raise RuntimeError((stderr or "no VTT produced")[:500])
        best = []
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as f:
                segs = parse_vtt(f.read())
            if len(segs) > len(best):
                best = segs
        if not best:
            raise RuntimeError("empty VTT")
        return best
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _from_api(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    if hasattr(api, "fetch"):
        fetched = api.fetch(video_id, languages=languages)
        return [
            {"start": round(float(s.start), 2), "end": round(float(s.start + s.duration), 2), "text": normalize_space(s.text)}
            for s in fetched if normalize_space(s.text)
        ]
    fetched = api.get_transcript(video_id, languages=languages)
    return [
        {"start": round(float(s["start"]), 2), "end": round(float(s["start"] + s["duration"]), 2), "text": normalize_space(s["text"])}
        for s in fetched if normalize_space(s["text"])
    ]


def fetch_transcript(url: str, video_id: str, languages: list[str] | None = None) -> dict[str, Any]:
    languages = languages or ["en"]
    errors = []
    try:
        segments = _from_ytdlp(url, video_id, languages)
        return {
            "status": "ok", "source": "youtube_captions", "language": "en",
            "segments": segments, "text": " ".join(s["text"] for s in segments),
            "segment_count": len(segments), "error": "",
        }
    except Exception as exc:
        errors.append(f"yt-dlp: {exc}")
    try:
        segments = _from_api(video_id, languages)
        if segments:
            return {
                "status": "ok", "source": "youtube_transcript_api", "language": "en",
                "segments": segments, "text": " ".join(s["text"] for s in segments),
                "segment_count": len(segments), "error": "",
            }
    except Exception as exc:
        errors.append(f"transcript-api: {exc}")
    return {"status": "no_captions", "source": "", "language": "", "segments": [], "text": "", "segment_count": 0, "error": " | ".join(errors)[:800]}
