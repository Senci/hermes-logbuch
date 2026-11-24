"""Plugin settings: plugins.entries.logbuch.settings with the config_schema defaults.

SCHEMA mirrors plugin.yaml (a test pins the two together). A value of the wrong type falls back to its
default, so a hand-edited config never breaks a route.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("logbuch.settings")

PLUGIN_ID = "logbuch"

SCHEMA: dict[str, tuple[str, Any]] = {
    "data_file": ("string", ""),
    "classify_model": ("string", "claude-haiku-5-5"),
    "provider": ("string", "anthropic"),
    "profile": ("string", "default"),
    "classify_limit": ("integer", 20),
}


def defaults() -> dict[str, Any]:
    return {key: default for key, (_kind, default) in SCHEMA.items()}


def read_entry() -> dict:
    """plugins.entries.logbuch.settings of the active profile's config; {} when Hermes is not importable."""
    try:
        from hermes_cli import config as hermes_config
    except ImportError:
        return {}
    loader = getattr(hermes_config, "load_config_readonly", None)
    if loader is None:
        return {}
    try:
        cfg = loader() or {}
        entry = ((cfg.get("plugins") or {}).get("entries") or {}).get(PLUGIN_ID) or {}
        settings = entry.get("settings")
        return settings if isinstance(settings, dict) else {}
    except Exception:
        log.debug("logbuch: config unreadable, using defaults", exc_info=True)
        return {}


def _coerce(kind: str, value: Any, default: Any) -> Any:
    if kind == "string":
        return value.strip() if isinstance(value, str) and value.strip() else default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return default
    return value


def load() -> dict[str, Any]:
    raw = read_entry()
    out = defaults()
    for key, (kind, default) in SCHEMA.items():
        if key in raw:
            out[key] = _coerce(kind, raw[key], default)
    return out
