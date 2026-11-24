"""Rules layer: git_repo_root/cwd, ticket keys and host names map to topic keys.

A rule that yields a topic AND a value emits a label (source `rule`, summary = title). A rule that yields
only a topic is a hint the model layer may take on. First rule with a value wins; otherwise the first
topic-only match becomes the hint. The rules come from the data file (lb_data).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from lb_topics import SUMMARY_MAX

PROMPT_WINDOW = 600


@dataclass(frozen=True)
class Rule:
    name: str
    field: str  # "path" (git_repo_root or cwd) or "text" (title plus the start of the first prompt)
    pattern: re.Pattern
    topic: str
    value: "int | Callable[[dict], int] | None" = None


def _fields(item: dict) -> dict[str, str]:
    path = " ".join(p for p in (item.get("git_repo_root"), item.get("cwd")) if p)
    text = f"{item.get('title') or ''} {(item.get('first_prompt') or '')[:PROMPT_WINDOW]}"
    return {"path": path, "text": text}


def evaluate(item: dict, rules: tuple[Rule, ...]) -> dict:
    """{label, hint, rule}: label is {topic, value, summary, source: 'rule'} or None, hint a topic or None."""
    fields = _fields(item)
    hint, hint_rule = None, None
    for rule in rules:
        if not rule.pattern.search(fields[rule.field]):
            continue
        if rule.value is None:
            if hint is None:
                hint, hint_rule = rule.topic, rule.name
            continue
        value = rule.value(item) if callable(rule.value) else rule.value
        summary = (item.get("title") or "(untitled)").strip()[:SUMMARY_MAX].rstrip()
        return {
            "label": {"topic": rule.topic, "value": value, "summary": summary, "source": "rule"},
            "hint": rule.topic,
            "rule": rule.name,
        }
    return {"label": None, "hint": hint, "rule": hint_rule}
