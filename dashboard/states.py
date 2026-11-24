"""Session state (D47): critical, waiting_go, interrupted, not_merged, todo, shipped, none.

Pure functions, no I/O (redaction is classify.redact). `analyze` reads the two texts that end a chain (its last digest reply and its last
assistant message) and returns message-derived facts that lb_scan caches with the chain. `decide` combines
those facts with the label value, the commit and MR call counts and the loose_end_done mark, which change
without the chain changing, and returns (state, state_evidence).

Highest wins: critical > waiting_go > interrupted > not_merged > todo > shipped > none.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

STATES = ("critical", "waiting_go", "interrupted", "not_merged", "todo", "shipped", "none")
EVIDENCE_MAX = 120
CONTEXT = 40

# Interrupt lines Hermes 0.22.2 writes when a provider call is cut short; a bare "Operation interrupted." names no cause.
INTERRUPT_PREFIXES = (
    "Operation interrupted: waiting for model response",
    "Operation interrupted: handling API error",
    "Operation interrupted: retrying API call after error",
    "Operation interrupted: waiting for the provider to recover",
    "Operation interrupted: retrying empty response from model",
    "Operation interrupted during retry",
)
# Failed-turn notices (agent/turn_failure_copy.py); rows written before Hermes types them carry no display_kind.
FAILED_TURN_NOTICES = (
    "Your request was not processed",
    "This turn did not complete",
)
CONTENT_POLICY = "content_policy_blocked"


@dataclass(frozen=True)
class StateFacts:
    """What the end of a chain says; evidence strings are already redacted and cut."""

    provider: str | None = None  # evidence of a provider-problem end, else None
    opens: tuple = ()  # ((state, evidence), ...) in the data file's open_states order


NO_FACTS = StateFacts()


def _flat(text: str | None) -> str:
    return " ".join((text or "").split())


def _cut(text: str) -> str:
    return text[:EVIDENCE_MAX].rstrip()


def _evidence(text: str | None) -> str:
    """Redact first (the model layer's one function), then cut: a cut first could split a key past its marker."""
    from classify import redact  # lazy: classify imports lb_service, which imports this module

    return _cut(_flat(redact(text or "")))


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _meta(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def provider_end(content: str | None, display_kind: str | None, display_metadata) -> str | None:
    """Evidence when the last assistant message is a provider problem, else None."""
    if display_kind == "failed_turn":
        meta = _meta(display_metadata)
        surface = meta.get("error_surface")
        surface = surface if isinstance(surface, dict) else {}
        error = _text(meta.get("error"))
        code = _text(surface.get("code"))
        if code == CONTENT_POLICY or error.startswith(CONTENT_POLICY):
            return None
        detail = error or content or "failed turn"
        label = code or _text(surface.get("layer"))
        if label and not detail.startswith(label):
            detail = f"{label}: {detail}"
        return _evidence(detail)
    text = (content or "").lstrip()
    if text.startswith(INTERRUPT_PREFIXES) or (not display_kind and text.startswith(FAILED_TURN_NOTICES)):
        return _evidence(text.split("\n", 1)[0])
    return None


def _snippet(raw_reply: str, match_text: str) -> str:
    """The matched text with a little context, from the redacted reply."""
    from classify import redact

    flat = _flat(redact(raw_reply))
    at = flat.lower().find(match_text.lower())
    if at < 0:
        return _cut(flat)
    return _cut(flat[max(0, at - CONTEXT):at + len(match_text) + CONTEXT].strip())


def open_ends(last_reply: str | None, window_chars: int, patterns: tuple) -> tuple:
    """Open states matched in the loose-end window (first window_chars) of the last digest reply."""
    window = _flat(last_reply)[:window_chars]
    out = []
    for state, pattern in patterns:
        m = pattern.search(window)
        if m:
            out.append((state, _snippet(last_reply or "", m.group(0))))
    return tuple(out)


def analyze(last_reply: str | None, last_message: dict | None, window_chars: int, patterns: tuple) -> StateFacts:
    """last_message is {content, display_kind, display_metadata} of the chain's last assistant message."""
    msg = last_message or {}
    provider = provider_end(msg.get("content"), msg.get("display_kind"), msg.get("display_metadata"))
    return StateFacts(provider=provider, opens=open_ends(last_reply, window_chars, patterns))


def decide(facts: StateFacts, value: int | None, commit_calls: int, mr_calls: int,
           loose_end_done: bool) -> tuple[str, str | None]:
    shipped = (commit_calls or 0) + (mr_calls or 0) > 0
    if loose_end_done:
        return ("shipped" if shipped else "none"), None
    opens = dict(facts.opens)
    if facts.provider is not None and value == 3:
        return "critical", facts.provider
    if "waiting_go" in opens:
        return "waiting_go", opens["waiting_go"]
    if facts.provider is not None:
        return "interrupted", facts.provider
    for state in ("not_merged", "todo"):
        if state in opens:
            return state, opens[state]
    return ("shipped" if shipped else "none"), None


def state_for(facts: StateFacts, item: dict) -> tuple[str, str | None]:
    """The one call the service makes per item; `item` carries label, commit_calls, mr_calls, loose_end_done."""
    label = item.get("label") or {}
    return decide(facts, label.get("value"), item.get("commit_calls", 0), item.get("mr_calls", 0),
                  bool(item.get("loose_end_done")))
