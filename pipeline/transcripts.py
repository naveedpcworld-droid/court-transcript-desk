"""Caption acquisition and VTT normalisation."""
from __future__ import annotations

import glob
import html
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .utils import normalize_space, run_cmd
from .innertube import fetch_innertube_transcript

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


def _from_supadata(url: str, languages: list[str], timeout: int = 60) -> list[dict[str, Any]]:
    key = os.environ.get("SUPADATA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("SUPADATA_API_KEY not set")
    qs = urllib.parse.urlencode({"url": url, "lang": languages[0] if languages else "en", "text": "false", "mode": "auto"})
    endpoint = f"https://api.supadata.ai/v1/transcript?{qs}"
    headers = {"x-api-key": key, "Content-Type": "application/json"}

    def get_json(u: str) -> dict[str, Any]:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    data = get_json(endpoint)
    if "jobId" in data:
        job = data["jobId"]
        for _ in range(30):
            time.sleep(2)
            data = get_json(f"https://api.supadata.ai/v1/transcript/{job}")
            if data.get("status") == "completed":
                break
            if data.get("status") in {"failed", "error"}:
                raise RuntimeError(f"Supadata job failed: {data}")
        else:
            raise RuntimeError("Supadata job timed out")
        data = data.get("result", data)
    content = data.get("content")
    if isinstance(content, str):
        return [{"start": 0.0, "end": 0.0, "text": normalize_space(content)}]
    segments = []
    for chunk in content or []:
        text = normalize_space(chunk.get("text", ""))
        if not text:
            continue
        start = round(float(chunk.get("offset", 0)) / 1000, 2)
        dur = round(float(chunk.get("duration", 0)) / 1000, 2)
        segments.append({"start": start, "end": round(start + max(dur, 0.4), 2), "text": text})
    return segments


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
        segments = fetch_innertube_transcript(video_id)
        if segments:
            return {
                "status": "ok", "source": "innertube", "language": "en",
                "segments": segments, "text": " ".join(s["text"] for s in segments),
                "segment_count": len(segments), "error": "",
            }
    except Exception as exc:
        errors.append(f"innertube: {exc}")
    if os.environ.get("SUPADATA_API_KEY", "").strip():
        try:
            segments = _from_supadata(url, languages)
            if segments:
                return {
                    "status": "ok", "source": "supadata", "language": "en",
                    "segments": segments, "text": " ".join(s["text"] for s in segments),
                    "segment_count": len(segments), "error": "",
                }
        except Exception as exc:
            errors.append(f"supadata: {exc}")
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
