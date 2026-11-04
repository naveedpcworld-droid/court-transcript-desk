"""JSON data store for the static-site pipeline."""
from __future__ import annotations

import os
from typing import Any

from .utils import atomic_write_json, now_utc, read_json


class Store:
    def __init__(self, root: str = "."):
        self.root = os.path.abspath(root)
        self.data_dir = os.path.join(self.root, "data")
        self.transcript_dir = os.path.join(self.data_dir, "transcripts")
        self.index_path = os.path.join(self.data_dir, "index.json")
        self.state_path = os.path.join(self.data_dir, "state.json")
        self.channels_path = os.path.join(self.data_dir, "channels.json")
        os.makedirs(self.transcript_dir, exist_ok=True)

    def load_index(self) -> dict[str, Any]:
        data = read_json(self.index_path, {}) or {}
        data.setdefault("generated_at", now_utc())
        data.setdefault("videos", [])
        data.setdefault("channels", [])
        return data

    def save_index(self, data: dict[str, Any]) -> None:
        data["generated_at"] = now_utc()
        atomic_write_json(self.index_path, data)

    def load_state(self) -> dict[str, Any]:
        data = read_json(self.state_path, {}) or {}
        data.setdefault("processed", {})
        data.setdefault("last_run", "")
        return data

    def save_state(self, data: dict[str, Any]) -> None:
        data["last_run"] = now_utc()
        atomic_write_json(self.state_path, data)

    def load_channels(self) -> dict[str, Any]:
        return read_json(self.channels_path, {}) or {}

    def save_channels(self, data: dict[str, Any]) -> None:
        atomic_write_json(self.channels_path, data)

    def video_ids(self, index: dict[str, Any]) -> set[str]:
        return {v["id"] for v in index.get("videos", []) if v.get("id")}

    def upsert_video(self, index: dict[str, Any], record: dict[str, Any]) -> None:
        videos = index.setdefault("videos", [])
        for i, existing in enumerate(videos):
            if existing.get("id") == record.get("id"):
                videos[i] = {**existing, **record}
                break
        else:
            videos.append(record)
        videos.sort(key=lambda v: (v.get("published") or "", v.get("id") or ""), reverse=True)

    def save_transcript(self, video_id: str, transcript: dict[str, Any]) -> str:
        path = os.path.join(self.transcript_dir, f"{video_id}.json")
        atomic_write_json(path, transcript)
        return f"data/transcripts/{video_id}.json"

    def transcript_path(self, video_id: str) -> str:
        return os.path.join(self.transcript_dir, f"{video_id}.json")
