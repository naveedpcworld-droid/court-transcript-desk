"""Build the static student site data from the private index."""
from __future__ import annotations

import argparse
import os
import shutil
from collections import Counter
from typing import Any

from .config import load_config
from .store import Store
from .utils import now_utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def duration_fmt(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=ROOT)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    settings, channels = load_config(os.path.join(root, "channels.yml"))
    store = Store(root)
    index = store.load_index()
    public = [v for v in index.get("videos", []) if v.get("public") and v.get("publish_transcript", True)]
    public.sort(key=lambda v: v.get("published") or "", reverse=True)

    site_data = os.path.join(root, "site", "data")
    tr_dir = os.path.join(site_data, "transcripts")
    os.makedirs(site_data, exist_ok=True)
    if os.path.isdir(tr_dir):
        shutil.rmtree(tr_dir)
    os.makedirs(tr_dir, exist_ok=True)

    out = []
    for v in public:
        rec = dict(v)
        rec["duration_fmt"] = duration_fmt(v.get("duration", 0))
        rec["published_date"] = (v.get("published") or "")[:10]
        rec["transcript_url"] = ""
        src = os.path.join(root, v.get("transcript_path") or "")
        if v.get("transcript_status") == "ok" and v.get("transcript_path") and os.path.exists(src):
            dst = os.path.join(tr_dir, f"{v['id']}.json")
            with open(src, "rb") as f, open(dst, "wb") as g:
                g.write(f.read())
            rec["transcript_url"] = f"data/transcripts/{v['id']}.json"
        out.append(rec)

    topic_counts = Counter()
    for v in out:
        for t in v.get("topic_labels") or []:
            topic_counts[t] += 1
    channel_counts = Counter(v.get("channel_name", "") for v in out)
    stats = {
        "videos": len(out),
        "transcripts": sum(1 for v in out if v.get("transcript_status") == "ok"),
        "channels": len(channel_counts),
        "topics": dict(topic_counts.most_common()),
        "latest_date": out[0].get("published") if out else "",
        "generated_at": now_utc(),
    }
    channel_rows = [
        {"name": name, "videos": n,
         "handle": next((v.get("channel_handle") for v in out if v.get("channel_name") == name), ""),
         "court": next((v.get("court") for v in out if v.get("channel_name") == name), "")}
        for name, n in channel_counts.most_common()
    ]
    from .utils import atomic_write_json
    atomic_write_json(os.path.join(site_data, "index.json"), {"generated_at": now_utc(), "videos": out})
    atomic_write_json(os.path.join(site_data, "stats.json"), stats)
    atomic_write_json(os.path.join(site_data, "channels.json"), channel_rows)
    atomic_write_json(os.path.join(site_data, "digest.json"), out[:20])

    # Minimal RSS for students who prefer a feed.
    items = []
    for v in out[:50]:
        link = v.get("url", "")
        items.append(
            f"<item><title>{escape(v.get('title',''))}</title><link>{escape(link)}</link>"
            f"<guid>{escape(v.get('id',''))}</guid><pubDate>{escape(v.get('published',''))}</pubDate>"
            f"<description>{escape(v.get('why',''))}</description></item>"
        )
    feed = f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Court Transcript Desk</title><link>./</link><description>New public court transcripts</description>{"".join(items)}</channel></rss>'
    with open(os.path.join(site_data, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(feed)
    print(f"site: {len(out)} public videos, {stats['transcripts']} transcripts, {len(channel_counts)} channels")
    return 0


def escape(value: Any) -> str:
    return (str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


if __name__ == "__main__":
    raise SystemExit(main())
