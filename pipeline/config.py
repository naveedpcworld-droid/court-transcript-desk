"""Load channels.yml and environment settings."""
from __future__ import annotations

from dataclasses import dataclass
import yaml


@dataclass
class Settings:
    timezone: str = "UTC"
    max_new_per_channel: int = 5
    max_total_new: int = 40
    backfill_new_channels: int = 0
    transcript_languages: list[str] | None = None
    public_site: bool = True

    def __post_init__(self):
        if self.transcript_languages is None:
            self.transcript_languages = ["en"]


@dataclass
class Channel:
    name: str
    handle: str
    source_tier: str
    rights_status: str
    public: bool
    publish_transcript: bool
    judge: str = ""
    court: str = ""
    notes: str = ""
    channel_id: str = ""
    monitor: bool = True


def load_config(path: str = "channels.yml") -> tuple[Settings, list[Channel]]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    s = raw.get("settings") or {}
    settings = Settings(
        timezone=s.get("timezone", "UTC"),
        max_new_per_channel=int(s.get("max_new_per_channel", 5)),
        max_total_new=int(s.get("max_total_new", 40)),
        backfill_new_channels=int(s.get("backfill_new_channels", 0)),
        transcript_languages=s.get("transcript_languages") or ["en"],
        public_site=bool(s.get("public_site", True)),
    )
    channels = []
    for c in raw.get("channels") or []:
        channels.append(Channel(
            name=c.get("name") or c.get("handle", "").lstrip("@"),
            handle=c.get("handle", ""),
            source_tier=c.get("source_tier", "unknown"),
            rights_status=c.get("rights_status", "unknown"),
            public=bool(c.get("public", False)),
            publish_transcript=bool(c.get("publish_transcript", False)),
            judge=c.get("judge", ""),
            court=c.get("court", ""),
            notes=c.get("notes", ""),
            channel_id=c.get("channel_id", ""),
            monitor=bool(c.get("monitor", True)),
        ))
    return settings, channels
