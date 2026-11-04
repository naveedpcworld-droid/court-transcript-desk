"""Resolve @handles to stable YouTube channel IDs and fetch channel RSS."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from .utils import http_get, normalize_space, strip_html

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
MEDIA = "{http://search.yahoo.com/mrss/}"


def resolve_channel_id(handle: str) -> str:
    clean = handle.strip()
    if clean.startswith("http"):
        url = clean.rstrip("/")
    else:
        url = f"https://www.youtube.com/{clean if clean.startswith('@') else '@' + clean}"
    html = http_get(url, timeout=30)
    patterns = [
        r'"externalId":"(UC[\w-]{22})"',
        r'"channelId":"(UC[\w-]{22})"',
        r'channel/(UC[\w-]{22})',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    raise RuntimeError(f"Could not resolve channel id for {handle}")


def fetch_rss(channel_id: str) -> list[dict[str, Any]]:
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    xml = http_get(url, timeout=30)
    root = ET.fromstring(xml)
    entries = []
    for entry in root.findall(f"{ATOM}entry"):
        vid = entry.findtext(f"{YT}videoId") or ""
        if not vid:
            continue
        title = normalize_space(strip_html(entry.findtext(f"{ATOM}title") or ""))
        published = entry.findtext(f"{ATOM}published") or ""
        desc_el = entry.find(f"{MEDIA}group/{MEDIA}description")
        description = strip_html(desc_el.text or "") if desc_el is not None else ""
        thumb_el = entry.find(f"{MEDIA}group/{MEDIA}thumbnail")
        thumbnail = thumb_el.attrib.get("url", "") if thumb_el is not None else ""
        entries.append({
            "id": vid,
            "title": title,
            "published": published,
            "description": normalize_space(description)[:4000],
            "thumbnail": thumbnail,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return entries
