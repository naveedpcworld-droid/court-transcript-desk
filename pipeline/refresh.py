"""Retry transcript gaps for already-known public videos."""
from __future__ import annotations

import argparse
import os

from .classify import classify_video
from .config import load_config
from .store import Store
from .transcripts import fetch_transcript
from .utils import now_utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args(argv)
    store = Store(args.root)
    settings, channels = load_config(os.path.join(args.root, "channels.yml"))
    cmap = {c.handle: c for c in channels}
    index = store.load_index()
    changed = 0
    for v in index.get("videos", []):
        if changed >= args.limit:
            break
        if not v.get("public") or not v.get("publish_transcript"):
            continue
        if v.get("transcript_status") == "ok":
            continue
        ch = cmap.get(v.get("channel_handle"))
        if not ch:
            continue
        tr = fetch_transcript(v["url"], v["id"], settings.transcript_languages)
        if tr.get("status") != "ok" or not tr.get("segments"):
            continue
        v["transcript_status"] = "ok"
        v["transcript_source"] = tr.get("source", "")
        v["transcript_segments"] = tr.get("segment_count", 0)
        v["transcript_path"] = store.save_transcript(v["id"], {
            "id": v["id"], "title": v["title"], "language": tr.get("language") or "en",
            "source": tr.get("source", ""), "fetched_at": now_utc(),
            "segments": tr["segments"], "text": tr["text"],
        })
        ex = classify_video(title=v["title"], description=v.get("description", ""),
                            transcript_text=tr["text"], default_judge=ch.judge, default_court=ch.court)
        for k in ("format", "topics", "primary_topic", "primary_topic_label", "topic_labels",
                  "judge", "court", "stage", "outcome", "case_name", "why", "confidence", "classifier"):
            v[k] = ex.get(k)
        store.save_index(index)
        changed += 1
        print("refreshed", v["id"], tr.get("source"))
    print("DONE refreshed", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
