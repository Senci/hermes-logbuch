"""The data file: topics, rules, loose-end and open-state phrases and the value rubric.

One JSON file, found in this order: the `data_file` setting, `$HERMES_HOME/logbuch/data.json`, else the
built-in neutral default below. Only `topics` is required; a missing section takes the default's.
A file that cannot be read or fails validation logs one error and the default stands in, so a bad
file never fails a route. The result is cached per file path, mtime and size.

Format (see examples/data.example.json):
  topics       {KEY: name}, at least one
  loose_end    regex (case-insensitive) matched on the start of a session's last reply
  open_states  {waiting_go|not_merged|todo: regex}, order is match order
  rubric       the value rubric sentence(s) in the model prompt
  rules        [{name, field: path|text, pattern: regex, topic, value}], value optional: absent or null is
               a topic hint only, an integer 0-3 labels, {"mr_calls_at_least": n, "value": a, "otherwise": b}
               labels a when the session has n or more MR calls, else b
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import lb_settings
from lb_rules import Rule
from lb_topics import VALUES

log = logging.getLogger("logbuch.data")

OPEN_STATES = ("waiting_go", "not_merged", "todo")
FILE_KEYS = {"topics", "loose_end", "open_states", "rubric", "rules"}
RULE_KEYS = {"name", "field", "pattern", "topic", "value"}
RULE_REQUIRED = RULE_KEYS - {"value"}
BRANCH_KEYS = {"mr_calls_at_least", "value", "otherwise"}
FIELDS = ("path", "text")

DEFAULT_RAW = {
    "topics": {
        "BUILD": "Features and fixes",
        "OPS": "Infrastructure and operations",
        "DOCS": "Docs, tickets and planning",
        "REVIEW": "Code review and repo hygiene",
        "TOOLS": "Tooling and agent setup",
        "PERSONAL": "Personal and miscellaneous",
    },
    "loose_end": (
        r"not processed|Operation interrupted|timed out|need(s)? your go|waiting on you|"
        r"still open|is still to do|none is merged|not merged|is a Draft|"
        r"decisions? (are )?(still )?(waiting|open)"
    ),
    "open_states": {
        "waiting_go": r"need(s)? your go|waiting on you|decisions? (are )?(still )?(waiting|open)",
        "not_merged": r"none is merged|not merged|is a Draft",
        "todo": r"still open|is still to do",
    },
    "rubric": (
        "3 = a production fix or a request from others delivered; 2 = team enablement or a "
        "decision on shared systems; 1 = indirect value; 0 = personal."
    ),
    "rules": [],
}


class DataError(ValueError):
    pass


@dataclass(frozen=True)
class Data:
    topics: dict
    loose: re.Pattern
    open_patterns: tuple  # ((state, pattern), ...) in match order
    rubric: str
    rules: tuple
    key: tuple  # identity of the source; changes when the file does


def _text(value, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{what} must be a non-empty string")
    return value


def _regex(value, what: str) -> re.Pattern:
    try:
        return re.compile(_text(value, what), re.I)
    except re.error as exc:
        raise DataError(f"{what} is not a valid regex: {exc}") from exc


def _int_value(value, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in VALUES:
        raise DataError(f"{what} must be an integer from 0 to 3")
    return value


def _branch_value(spec: dict, what: str):
    if set(spec) != BRANCH_KEYS:
        raise DataError(f"{what} must have exactly {', '.join(sorted(BRANCH_KEYS))}")
    at_least = spec["mr_calls_at_least"]
    if isinstance(at_least, bool) or not isinstance(at_least, int) or at_least < 1:
        raise DataError(f"{what}.mr_calls_at_least must be an integer of at least 1")
    high, low = _int_value(spec["value"], f"{what}.value"), _int_value(spec["otherwise"], f"{what}.otherwise")
    return lambda item: high if item.get("mr_calls", 0) >= at_least else low


def _rule(spec, n: int, topics: dict) -> Rule:
    what = f"rules[{n}]"
    if not isinstance(spec, dict):
        raise DataError(f"{what} must be an object")
    missing, unknown = RULE_REQUIRED - set(spec), set(spec) - RULE_KEYS
    if missing or unknown:
        raise DataError(f"{what} needs {', '.join(sorted(RULE_REQUIRED))} and may add value")
    if spec["field"] not in FIELDS:
        raise DataError(f"{what}.field must be one of {', '.join(FIELDS)}")
    if spec["topic"] not in topics:
        raise DataError(f"{what}.topic is not a key of topics")
    raw_value = spec.get("value")
    if raw_value is None:
        value = None
    elif isinstance(raw_value, dict):
        value = _branch_value(raw_value, f"{what}.value")
    else:
        value = _int_value(raw_value, f"{what}.value")
    return Rule(_text(spec["name"], f"{what}.name"), spec["field"], _regex(spec["pattern"], f"{what}.pattern"),
                spec["topic"], value)


def parse(raw, key: tuple) -> Data:
    """Validate a decoded file and compile it; DataError names the first problem."""
    if not isinstance(raw, dict):
        raise DataError("the file must be a JSON object")
    unknown = set(raw) - FILE_KEYS
    if unknown:
        raise DataError(f"unknown key(s): {', '.join(sorted(unknown))}")
    if "topics" not in raw:
        raise DataError("topics is required")
    merged = dict(DEFAULT_RAW, **raw)
    topics = merged["topics"]
    if not isinstance(topics, dict) or not topics:
        raise DataError("topics must be an object with at least one key")
    for name, label in topics.items():
        _text(name, "a topics key")
        _text(label, f"topics.{name}")
    states = merged["open_states"]
    if not isinstance(states, dict) or set(states) - set(OPEN_STATES):
        raise DataError(f"open_states must be an object with keys from {', '.join(OPEN_STATES)}")
    rules = merged["rules"]
    if not isinstance(rules, list):
        raise DataError("rules must be a list")
    built = tuple(_rule(spec, n, topics) for n, spec in enumerate(rules))
    names = [rule.name for rule in built]
    if len(set(names)) != len(names):
        raise DataError("rule names must be unique")
    return Data(
        topics=dict(topics),
        loose=_regex(merged["loose_end"], "loose_end"),
        open_patterns=tuple((state, _regex(pattern, f"open_states.{state}")) for state, pattern in states.items()),
        rubric=_text(merged["rubric"], "rubric"),
        rules=built,
        key=key,
    )


DEFAULT = parse(DEFAULT_RAW, ("default",))

_cache: dict[str, tuple[tuple, Data]] = {}
_lock = threading.Lock()


def _signature(path: Path) -> tuple:
    try:
        st = path.stat()
    except OSError:
        return (str(path), None, None)
    return (str(path), st.st_mtime_ns, st.st_size)


def _read(path: Path, sig: tuple) -> Data:
    try:
        return parse(json.loads(path.read_text(encoding="utf-8")), sig)
    except (OSError, ValueError) as exc:
        log.error("logbuch: data file %s is unusable, the built-in default stands in: %s", path, exc)
        return DEFAULT


def load(home: Path) -> Data:
    configured = lb_settings.load()["data_file"]
    path = Path(configured).expanduser() if configured else Path(home) / "logbuch" / "data.json"
    if not configured and not path.is_file():
        return DEFAULT
    sig = _signature(path)
    with _lock:
        cached = _cache.get(sig[0])
        if cached is not None and cached[0] == sig:
            return cached[1]
        data = _read(path, sig)
        _cache[sig[0]] = (sig, data)
        return data
