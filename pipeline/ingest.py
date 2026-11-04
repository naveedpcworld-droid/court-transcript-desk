"""Detect new uploads, fetch metadata/captions, classify, and store records."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .classify import classify_video
from .config import Channel, Settings, load_config
from .resolve import fetch_rss, resolve_channel_id
from .store import Store
from .transcripts import fetch_transcript
from .utils import now_utc, parse_duration, parse_published, parse_views, run_cmd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(msg: str) -> None:
    print(msg, flush=True)


def ytdlp_metadata(url: str) -> dict[str, Any] | None:
    code, out, err = run_cmd(
        ["yt-dlp", "--dump-single-json", "--no-warnings", "--no-playlist", url],
        timeout=150,
    )
    if code != 0 or not out.strip():
        log(f"  ! metadata failed: {(err or '')[:240]}")
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def build_record(ch: Channel, entry: dict[str, Any], meta: dict[str, Any] | None,
                 settings: Settings, store: Store) -> dict[str, Any]:
    meta = meta or {}
    video_id = entry["id"]
    title = meta.get("title") or entry.get("title") or video_id
    description = (meta.get("description") or entry.get("description") or "")[:4000]
    duration = parse_duration(meta.get("duration"))
    views = parse_views(meta.get("view_count"))
    published = parse_published(meta.get("upload_date") or entry.get("published"))
    thumbnail = meta.get("thumbnail") or entry.get("thumbnail") or ""
    restricted_rights = ch.rights_status in {"no_recording_order", "commentary_internal_only", "unknown"}
    can_fetch = bool(ch.publish_transcript) and not restricted_rights
    transcript = {"status": "restricted", "segments": [], "text": "", "source": "", "segment_count": 0}
    transcript_path = ""
    if can_fetch:
        transcript = fetch_transcript(entry["url"], video_id, settings.transcript_languages)
        if transcript.get("status") == "ok" and transcript.get("segments"):
            transcript_path = store.save_transcript(video_id, {
                "id": video_id,
                "title": title,
                "language": transcript.get("language") or "en",
                "source": transcript.get("source", ""),
                "fetched_at": now_utc(),
                "segments": transcript["segments"],
                "text": transcript["text"],
            })
        else:
            log(f"  - no captions: {video_id} {transcript.get('error','')[:180]}")
    elif ch.rights_status == "no_recording_order":
        transcript["status"] = "blocked_rights"
    elif ch.rights_status in {"commentary_internal_only", "unknown"}:
        transcript["status"] = "restricted"
    elif not ch.publish_transcript:
        transcript["status"] = "restricted"

    extracted = classify_video(
        title=title, description=description,
        transcript_text=transcript.get("text", ""),
        channel_name=ch.name, default_judge=ch.judge, default_court=ch.court,
    )
    return {
        "id": video_id,
        "title": title,
        "channel_id": meta.get("channel_id") or "",
        "channel_handle": ch.handle,
        "channel_name": ch.name,
        "source_tier": ch.source_tier,
        "rights_status": ch.rights_status,
        "public": bool(ch.public),
        "publish_transcript": bool(ch.publish_transcript),
        "published": published,
        "duration": duration,
        "views": views,
        "url": entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": thumbnail,
        "description": description,
        "transcript_status": transcript.get("status", "error"),
        "transcript_source": transcript.get("source", ""),
        "transcript_path": transcript_path,
        "transcript_segments": int(transcript.get("segment_count") or 0),
        "format": extracted.get("format", "single_case"),
        "topics": extracted["topics"],
        "primary_topic": extracted["primary_topic"],
        "primary_topic_label": extracted["primary_topic_label"],
        "topic_labels": extracted["topic_labels"],
        "judge": extracted["judge"],
        "court": extracted["court"],
        "stage": extracted["stage"],
        "outcome": extracted["outcome"],
        "case_name": extracted["case_name"],
        "why": extracted["why"],
        "confidence": extracted["confidence"],
        "classifier": extracted["classifier"],
        "processed_at": now_utc(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join(ROOT, "channels.yml"))
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--channel", default="", help="Only this handle/name")
    parser.add_argument("--max-new", type=int, default=0, help="Override total new limit")
    parser.add_argument("--backfill", type=int, default=-1, help="Override per-channel backfill")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    settings, channels = load_config(args.config)
    store = Store(args.root)
    index = store.load_index()
    state = store.load_state()
    cache = store.load_channels()
    processed = state.setdefault("processed", {})
    known = store.video_ids(index) | set(processed.keys())
    max_total = args.max_new or settings.max_total_new
    added = 0

    channel_meta = {c.get("handle"): c for c in index.get("channels", [])}
    for ch in channels:
        if not ch.monitor:
            continue
        if args.channel and args.channel.lower() not in {ch.handle.lower(), ch.name.lower(), ch.handle.lstrip("@").lower()}:
            continue
        try:
            was_cached = ch.handle in cache
            cid = ch.channel_id or cache.get(ch.handle, {}).get("id") or ""
            if not cid:
                cid = resolve_channel_id(ch.handle)
                cache[ch.handle] = {"id": cid, "name": ch.name, "resolved_at": now_utc()}
                store.save_channels(cache)
            channel_meta[ch.handle] = {
                "handle": ch.handle, "name": ch.name, "channel_id": cid,
                "source_tier": ch.source_tier, "rights_status": ch.rights_status,
                "public": ch.public, "court": ch.court, "judge": ch.judge,
            }
            log(f"[{ch.name}] {cid}")
            rss = fetch_rss(cid)
            new_entries = [e for e in rss if e["id"] not in known]
            limit = settings.max_new_per_channel
            if args.backfill >= 0:
                limit = args.backfill
            elif settings.backfill_new_channels and not was_cached:
                limit = max(limit, settings.backfill_new_channels)
            for entry in new_entries[:limit]:
                if added >= max_total:
                    break
                if entry["id"] in known:
                    continue
                log(f"  + {entry['id']} {entry['title'][:80]}")
                meta = ytdlp_metadata(entry["url"])
                record = build_record(ch, entry, meta, settings, store)
                if args.dry_run:
                    log(f"    DRY {record['transcript_status']} topics={record['topics']}")
                else:
                    store.upsert_video(index, record)
                    processed[entry["id"]] = now_utc()
                    known.add(entry["id"])
                    added += 1
                    store.save_index(index)
                    store.save_state(state)
                if added >= max_total:
                    break
        except Exception as exc:
            log(f"  ERROR {ch.handle}: {exc}")
            continue

    index["channels"] = [channel_meta[k] for k in sorted(channel_meta)]
    if not args.dry_run:
        store.save_index(index)
        store.save_state(state)
    log(f"DONE added={added} total={len(index.get('videos', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
