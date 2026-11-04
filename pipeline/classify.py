"""Deterministic case/judge/topic classification."""
from __future__ import annotations

import re
from typing import Any

from .taxonomy import CATEGORIES, TOPIC_ORDER, STAGE_PATTERNS, OUTCOME_PATTERNS

JUDGE_RE = re.compile(r"\bJudge\s+([A-Z][a-zA-Z'’.-]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-zA-Z'’.-]+)?)")
JUDGE_STOP = {
    "DESTROYS", "DESTROYED", "SHUTS", "SHUT", "SNAPS", "SNAPPED", "GOES", "LOSES", "SENDS", "SENT",
    "THROWS", "RIPS", "BLASTS", "EXPOSES", "EXPOSED", "DEMANDS", "WARNS", "HUMILIATES", "ENDS",
    "CRUSHES", "OBLITERATES", "ERUPTS", "STUNS", "STUNNED", "SLAPS", "GIVES", "HAS", "SAYS",
    "SAID", "ORDERS", "ORDERED", "FIRST", "APPEARANCE", "COURTROOM", "HEARING", "SENTENCING",
    "TRIAL", "CASE", "RULING", "THE", "A", "AN",
}
CASE_RE = re.compile(
    r"\b(?:State|People|United States|Commonwealth|City|County)\s+(?:of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+)?"
    r"(?:v\.?|versus|vs\.?)\s+([A-Z][a-zA-Z'’.-]+(?:\s+[A-Z][a-zA-Z'’.-]+){0,3})"
)


def extract_judge(text: str, default: str = "") -> str:
    for m in JUDGE_RE.finditer(text or ""):
        raw = m.group(1).strip().replace("’s", "").replace("'s", "")
        parts = raw.split()
        if not parts or parts[0].upper() in JUDGE_STOP:
            continue
        if len(parts) > 2 and re.fullmatch(r"[A-Z]\.", parts[1]):
            parts = [parts[0]] + parts[2:]
        if len(parts) > 1 and (parts[1].isupper() or parts[1].lower() in {"gives", "gave", "shuts", "snaps"}):
            parts = parts[:1]
        name = " ".join(parts)
        if name and "Courtroom" not in name and "Hearing" not in name:
            return name
    return default


def topic_scores(text: str) -> dict[str, int]:
    scores = {}
    for key, meta in CATEGORIES.items():
        count = 0
        for pat in meta["patterns"]:
            count += len(re.findall(pat, text, re.I))
        if count:
            scores[key] = count
    return scores


def extract_stage(text: str) -> str:
    for stage, pats in STAGE_PATTERNS:
        if any(re.search(p, text, re.I) for p in pats):
            return stage
    return "hearing"


def extract_outcome(text: str) -> str:
    for label, pats in OUTCOME_PATTERNS:
        for p in pats:
            m = re.search(p, text, re.I)
            if m:
                if m.groups():
                    return f"{label}: {m.group(1).strip()[:120]}"
                return label
    return ""


def extract_case_name(text: str) -> str:
    m = CASE_RE.search(text or "")
    return m.group(0)[:160] if m else ""


def classify_video(*, title: str, description: str, transcript_text: str, channel_name: str = "",
                   default_judge: str = "", default_court: str = "") -> dict[str, Any]:
    # The title is a stronger signal than the body; weight it heavily by repeating it.
    title_text = " ".join([title or ""] * 4)
    body = (transcript_text or "")[:12000]
    mixed = f"{title_text} {description or ''} {body}"
    scores = topic_scores(mixed)
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], TOPIC_ORDER.index(kv[0])))
    topics = [k for k, _ in ordered[:6]]
    primary = topics[0] if topics else "other"
    judge = extract_judge(f"{title} {body}", default_judge)
    if judge and default_judge and judge.split()[-1].lower() in default_judge.lower():
        judge = default_judge
    is_docket = bool(re.search(r"\bdocket\b|personal meeting room|morning docket|afternoon dock", title or "", re.I))
    stage = extract_stage(mixed)
    outcome = extract_outcome(mixed[:20000])
    case_name = extract_case_name(f"{title} {body[:5000]}")
    confidence = 0.35
    if topics:
        confidence += 0.2
    if judge:
        confidence += 0.15
    if len(body) > 500:
        confidence += 0.15
    if outcome:
        confidence += 0.1
    confidence = round(min(confidence, 0.95), 2)
    why = CATEGORIES[primary]["why"] if primary in CATEGORIES else "A public court hearing with a clear procedural story."
    if is_docket and len(topics) > 2:
        primary = "mixed_docket"
        why = "A multi-case docket with several short hearings; clip the strongest exchange."
    return {
        "format": "docket" if is_docket else "single_case",
        "topics": topics,
        "primary_topic": primary,
        "primary_topic_label": "Mixed docket" if primary == "mixed_docket" else (CATEGORIES[primary]["label"] if primary in CATEGORIES else "Other"),
        "topic_labels": [CATEGORIES[t]["label"] for t in topics],
        "judge": judge or default_judge,
        "court": default_court,
        "stage": stage,
        "outcome": outcome,
        "case_name": case_name,
        "why": why,
        "confidence": confidence,
        "classifier": "rules-v1",
    }
