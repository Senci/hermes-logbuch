"""Shared test helpers: fastapi stand-in, synthetic state.db builder, plugin loader.

Synthetic data only. No live paths: every db and home lives under a TemporaryDirectory, and the
settings read is stubbed so a test never sees the config of the machine it runs on.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
DASHBOARD = PLUGIN / "dashboard"
sys.path.insert(0, str(DASHBOARD))

import lb_data  # noqa: E402
import lb_settings  # noqa: E402

REAL_READ_ENTRY = lb_settings.read_entry
SETTINGS: dict = {}
lb_settings.read_entry = lambda: dict(SETTINGS)

TEST_RAW = {
    "topics": {
        "SHOP": "Storefront",
        "BILL": "Billing",
        "LAUNCH": "Launch week",
        "SYNC": "Sync jobs",
        "EDGE": "Edge caches",
        "OPS": "Infra ops",
        "GIT": "Repo hygiene",
        "WS": "Workstation",
    },
    "loose_end": (
        r"not processed|Operation interrupted|timed out|need(s)? your go|waiting on you|"
        r"still open|is still to do|Still to do|none is merged|not merged|is a Draft|"
        r"decisions? (are )?(still )?(waiting|open)|picker timed out"
    ),
    "open_states": {
        "waiting_go": r"need(s)? your go|waiting on you|decisions? (are )?(still )?(waiting|open)|picker timed out",
        "not_merged": r"none is merged|not merged|is a Draft",
        "todo": r"still open|is still to do|Still to do",
    },
    "rubric": "3 = shipped for others; 2 = team enablement; 1 = indirect value; 0 = personal.",
    "rules": [
        {"name": "path:launch", "field": "path", "pattern": r"/src/launch(-wt)?(/|$)", "topic": "LAUNCH",
         "value": {"mr_calls_at_least": 5, "value": 3, "otherwise": 2}},
        {"name": "path:billing", "field": "path", "pattern": r"/src/billing(/|$)", "topic": "BILL", "value": 3},
        {"name": "path:shop", "field": "path", "pattern": r"/src/shop(/|$)", "topic": "SHOP", "value": 3},
        {"name": "path:sync", "field": "path", "pattern": r"/src/sync(/|$)", "topic": "SYNC"},
        {"name": "ticket:BILLING", "field": "text", "pattern": r"\bBILLING-\d+", "topic": "LAUNCH"},
        {"name": "host:edge", "field": "text", "pattern": r"\bedge-(cache|proxy)-\d+|\bcache(-test)?\.example\.org",
         "topic": "EDGE"},
        {"name": "host:shop-db", "field": "text", "pattern": r"\bshop-db-\d+", "topic": "SHOP", "value": 3},
        {"name": "host:ops", "field": "text", "pattern": r"\bops-(vault|mail)-\d+|\bterraform\b", "topic": "OPS"},
    ],
}
DATA = lb_data.parse(TEST_RAW, ("test",))


def write_data(path: Path, raw: dict | None = None) -> Path:
    path.write_text(json.dumps(TEST_RAW if raw is None else raw), encoding="utf-8")
    return path


def use_settings(case, **values) -> None:
    """Set plugin settings for one test; the stubbed read returns them until the test ends."""
    SETTINGS.update(values)
    case.addCleanup(SETTINGS.clear)

SESSION_COLS = {
    "id": "text primary key", "source": "text not null", "parent_session_id": "text",
    "started_at": "real not null", "last_activity_at": "real", "ended_at": "real", "title": "text",
    "cwd": "text", "git_repo_root": "text", "message_count": "integer default 0",
    "tool_call_count": "integer default 0",
}
MESSAGE_COLS = {
    "id": "integer primary key autoincrement", "session_id": "text not null", "role": "text not null",
    "content": "text", "tool_calls": "text", "display_kind": "text", "display_metadata": "text",
}


def install_fastapi_stand_in() -> None:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def _deco(self, _path: str):
            return lambda fn: fn

        get = put = post = _deco

    def Query(default=None, **_kw):
        return default

    class Response:
        def __init__(self, content="", media_type=None, **_kw):
            self.body = content.encode() if isinstance(content, str) else content
            self.media_type = media_type

    mod = types.ModuleType("fastapi")
    mod.APIRouter, mod.HTTPException, mod.Query, mod.Response = APIRouter, HTTPException, Query, Response
    sys.modules["fastapi"] = mod


def load_api():
    """Import dashboard/plugin_api.py by path, as the dashboard does; stand-in when fastapi is absent."""
    try:
        import fastapi  # noqa: F401
    except ImportError:
        install_fastapi_stand_in()
    name = "logbuch_plugin_api_under_test"
    spec = importlib.util.spec_from_file_location(name, DASHBOARD / "plugin_api.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_state_db(path: Path, drop_session=(), drop_message=()) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    scols = ", ".join(f"{c} {t}" for c, t in SESSION_COLS.items() if c not in drop_session)
    mcols = ", ".join(f"{c} {t}" for c, t in MESSAGE_COLS.items() if c not in drop_message)
    conn.execute(f"create table sessions ({scols})")
    conn.execute(f"create table messages ({mcols})")
    return conn


def add_session(conn, sid, source="desktop", parent=None, started=1000.0, last=None, ended=None,
                title=None, cwd=None, repo=None, tool_calls=0):
    values = {
        "id": sid, "source": source, "parent_session_id": parent, "started_at": started,
        "last_activity_at": last, "ended_at": ended, "title": title, "cwd": cwd, "git_repo_root": repo,
        "message_count": 0, "tool_call_count": tool_calls,
    }
    cols = [c for c in conn.execute("pragma table_info(sessions)").fetchall()]
    names = [c[1] for c in cols]
    conn.execute(
        f"insert into sessions ({', '.join(names)}) values ({', '.join('?' * len(names))})",
        [values[n] for n in names],
    )


def add_message(conn, sid, role, content="", calls=None, kind=None, meta=None):
    names = [c[1] for c in conn.execute("pragma table_info(messages)").fetchall() if c[1] != "id"]
    row = {"session_id": sid, "role": role, "content": content, "tool_calls": calls,
           "display_kind": kind, "display_metadata": meta}
    conn.execute(
        f"insert into messages ({', '.join(names)}) values ({', '.join('?' * len(names))})",
        [row[n] for n in names],
    )


def raw_calls(name: str, command: str | None = None) -> str:
    """tool_calls text with the exact `"name": "x"` spacing the prototype's LIKE patterns look for."""
    arg = f', "arguments": {json.dumps(json.dumps({"command": command}))}' if command else ""
    return f'[{{"id": "c1", "function": {{"name": "{name}"{arg}}}}}]'


def build_world(path: Path, **kw) -> sqlite3.Connection:
    """A small world: one folded chain, a qualifying cli root, and roots that must not qualify."""
    conn = make_state_db(path, **kw)
    add_session(conn, "A", "desktop", started=100, last=5000, tool_calls=15, title="Alpha\nwork")
    add_session(conn, "A2", "kanban", parent="A", started=200, last=9000, tool_calls=10)
    add_session(conn, "B", "cli", started=300, last=400, tool_calls=30, title="Reads only")
    add_session(conn, "C", "cli", started=500, ended=7000, tool_calls=25)
    add_session(conn, "D", "desktop", started=600, last=700, tool_calls=5, title="Too small")
    add_session(conn, "E", "kanban", started=800, last=900, tool_calls=50, title="Worker run")
    add_session(conn, "G", "oneshot", started=950, last=960, tool_calls=40)
    # A: 1 user turn, 2 write_file + 1 patch rows, 1 commit row
    add_message(conn, "A", "user", "start the task please")
    add_message(conn, "A", "assistant", "", raw_calls("write_file"))
    add_message(conn, "A", "assistant", "", raw_calls("write_file"))
    add_message(conn, "A", "assistant", "", raw_calls("patch"))
    add_message(conn, "A", "assistant", "", raw_calls("terminal", "git commit -m x"))
    # A2 (compression child, folded into A): 2 user turns, 1 MR create, 1 gh pr create, final reply
    add_message(conn, "A2", "user", "continue")
    add_message(conn, "A2", "user", "and more")
    add_message(conn, "A2", "assistant", "", raw_calls("terminal", "glab mr create --fill"))
    add_message(conn, "A2", "assistant", "", raw_calls("terminal", "gh pr create"))
    add_message(conn, "A2", "assistant", "Done, but the MR still open and needs your go before anything lands.")
    # B: reads only
    add_message(conn, "B", "user", "look around")
    add_message(conn, "B", "assistant", "", raw_calls("read_file"))
    # C: kanban cards only
    add_message(conn, "C", "user", "plan the board")
    add_message(conn, "C", "assistant", "", raw_calls("kanban_create"))
    # D, E: signals but the wrong size or source
    add_message(conn, "D", "assistant", "", raw_calls("write_file"))
    add_message(conn, "E", "assistant", "", raw_calls("write_file"))
    conn.commit()
    return conn
