"""Service layer behind the routes: assemble items, merge labels, serve the digest.

Precedence manual > llm > rule: a stored label (manual or llm) wins over the computed rule label.
The model layer (/classify) builds on `unlabelled_items` and `store_llm_label`.
"""

from __future__ import annotations

import time
from pathlib import Path

import lb_data
import lb_digest
import lb_labels
import lb_rules
import lb_scan
import states as lb_states
from lb_topics import SUMMARY_MAX, VALUES

PATCH_KEYS = {"topic", "value", "summary", "loose_end_done"}
LABEL_KEYS = {"topic", "value", "summary"}


class ServiceError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _state_db(home: Path) -> Path:
    return Path(home) / "state.db"


def _view(home: Path) -> tuple[lb_data.Data, lb_scan.Snapshot, list[tuple[lb_scan.Entry, dict, dict]]]:
    data = lb_data.load(home)
    snap = lb_scan.scanner_for(_state_db(home)).refresh(data)
    stored, done = lb_labels.read_all(home)
    rows = []
    for entry in snap.entries:
        base = entry.item or {}
        rule_input = dict(base, cwd=entry.cwd, git_repo_root=entry.git_repo_root, first_prompt=entry.first_prompt)
        rule = lb_rules.evaluate(rule_input, data.rules)
        label = stored.get(base["id"]) or rule["label"]
        item = dict(base, loose_end_done=base["id"] in done, label=dict(label) if label else None)
        item["state"], item["state_evidence"] = lb_states.state_for(entry.facts, item)
        rows.append((entry, item, rule))
    return data, snap, rows


def sessions_payload(home: Path, profile: str) -> dict:
    data, snap, rows = _view(home)
    return {
        "generated_at": time.time(),
        "profile": profile,
        "schema_ok": snap.schema_ok,
        "topics": dict(data.topics),
        "items": [item for _e, item, _r in rows],
    }


def _find(home: Path, session_id: str) -> dict | None:
    _data, _snap, rows = _view(home)
    for _e, item, _r in rows:
        if item["id"] == session_id:
            return item
    return None


def _clean_summary(raw) -> str:
    if not isinstance(raw, str):
        raise ServiceError(422, "summary must be a string")
    text = " ".join(raw.split())[:SUMMARY_MAX].rstrip()
    if not text:
        raise ServiceError(422, "summary must not be empty")
    return text


def put_label(home: Path, session_id: str, body) -> dict:
    item = _find(home, session_id)
    if item is None:
        raise ServiceError(404, f"unknown session {session_id}")
    if not isinstance(body, dict) or not body:
        raise ServiceError(422, "body must be an object with topic, value, summary or loose_end_done")
    unknown = sorted(set(body) - PATCH_KEYS)
    if unknown:
        raise ServiceError(422, f"unknown field(s): {', '.join(unknown)}")
    flag = None
    if "loose_end_done" in body:
        if not isinstance(body["loose_end_done"], bool):
            raise ServiceError(422, "loose_end_done must be true or false")
        flag = body["loose_end_done"]
    merged = None
    if LABEL_KEYS & set(body):
        existing = item["label"] or {}
        merged = {k: existing.get(k) for k in ("topic", "value", "summary")}
        for key in ("topic", "value", "summary"):
            if key in body:
                merged[key] = body[key]
        topics = lb_data.load(home).topics
        if merged["topic"] not in topics:
            raise ServiceError(422, f"topic must be one of {', '.join(topics)}")
        value = merged["value"]
        if isinstance(value, bool) or not isinstance(value, int) or value not in VALUES:
            raise ServiceError(422, "value must be an integer from 0 to 3")
        merged["summary"] = _clean_summary(merged["summary"] if merged["summary"] is not None else item["title"])
    lb_labels.put_manual(home, session_id, merged, flag)
    updated = _find(home, session_id)
    if updated is None:
        raise ServiceError(404, f"unknown session {session_id}")
    return updated


def unlabelled_items(home: Path, limit: int | None = None) -> list[dict]:
    """Items with no label at all (no manual, llm or rule label), newest first, for the model layer.

    Each is {id, title, first_prompt, last_reply, topic_hint}; the texts are raw (up to 4000 chars) so
    the caller can redact before it cuts. topic_hint is a topic-only rule match or None.
    """
    _data, _snap, rows = _view(home)
    out = []
    for entry, item, rule in rows:
        if item["label"] is not None:
            continue
        out.append({
            "id": item["id"], "title": item["title"], "first_prompt": entry.first_prompt,
            "last_reply": entry.last_reply, "topic_hint": rule["hint"],
        })
        if limit is not None and len(out) >= limit:
            break
    return out


def store_llm_label(home: Path, session_id: str, topic: str, value: int, summary: str) -> bool:
    """Store a model label; a manual label is never touched. False when refused or not a valid label."""
    if topic not in lb_data.load(home).topics or isinstance(value, bool) or value not in VALUES:
        return False
    try:
        text = _clean_summary(summary)
    except ServiceError:
        return False
    return lb_labels.put_llm(home, session_id, topic, value, text)


def digest_markdown(home: Path, week: str | None) -> tuple[str, str]:
    week = lb_digest.current_week() if week is None else week
    try:
        lb_digest.parse_week(week)
    except lb_digest.BadWeek as exc:
        raise ServiceError(400, str(exc)) from exc
    data, _snap, rows = _view(home)
    return week, lb_digest.render(week, [item for _e, item, _r in rows], data.topics)


def digest_file(home: Path, week: str | None) -> dict:
    if not isinstance(week, str):
        raise ServiceError(400, "week must be a string like 2026-W43")
    week, text = digest_markdown(home, week)
    path = lb_digest.write_file(home, week, text)
    return {"path": str(path), "name": path.name}
