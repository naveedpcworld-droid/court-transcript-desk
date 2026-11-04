"""Fetch YouTube transcript panels through the public InnerTube endpoint.

This is the provider that works from GitHub-hosted runners even when the
watch page / yt-dlp is blocked by YouTube's bot check.
"""
from __future__ import annotations

import base64
import json
import urllib.request
from typing import Any

from .utils import normalize_space

CLIENT_VERSION = "2.20261029.11.00"
ENDPOINT = "https://www.youtube.com/youtubei/v1/get_panel?prettyPrint=false"


def _params(video_id: str) -> str:
    raw = bytes([0xAA, 0x09, 0x0F, 0x0A, 0x0B]) + video_id.encode() + bytes([0x18, 0x01])
    return base64.b64encode(raw).decode()


def _seconds(stamp: str) -> float:
    try:
        p = [int(x) for x in str(stamp).split(":")]
    except ValueError:
        return 0.0
    if len(p) == 3:
        return p[0] * 3600 + p[1] * 60 + p[2]
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return float(p[0]) if p else 0.0


def fetch_innertube_transcript(video_id: str, timeout: int = 45) -> list[dict[str, Any]]:
    body = {
        "context": {"client": {"hl": "en", "gl": "US", "clientName": "WEB", "clientVersion": CLIENT_VERSION}},
        "panelId": "PAmodern_transcript_view",
        "params": _params(video_id),
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
            "X-Youtube-Client-Name": "1",
            "X-Youtube-Client-Version": CLIENT_VERSION,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    raw = []
    seen = set()

    def walk(o):
        if not o or id(o) in seen:
            return
        seen.add(id(o))
        if isinstance(o, list):
            for item in o:
                walk(item)
            return
        if not isinstance(o, dict):
            return
        if "transcriptSegmentViewModel" in o:
            s = o["transcriptSegmentViewModel"]
            text = normalize_space(s.get("simpleText") or " ".join(x.get("text", "") for x in (s.get("text", {}).get("runs") or [])))
            if text:
                raw.append({"timestamp": s.get("timestamp", ""), "text": text})
        for v in o.values():
            if isinstance(v, (dict, list)):
                walk(v)

    walk(data)
    # Convert timestamps; the panel does not expose end times, so use the next start.
    segments = []
    for i, s in enumerate(raw):
        start = _seconds(s["timestamp"])
        end = _seconds(raw[i + 1]["timestamp"]) if i + 1 < len(raw) else start + 4.0
        if end <= start:
            end = start + 1.0
        segments.append({"start": round(start, 2), "end": round(end, 2), "text": s["text"]})
    return segments
