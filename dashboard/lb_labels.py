"""Label store: $HERMES_HOME/logbuch/labels.db, created on the first write, never on a read.

Table `labels` holds llm and manual labels (rule labels are computed, not stored); `flags` holds the
loose_end_done mark, which exists independently of any label. Precedence is manual > llm > rule and a
manual label is never overwritten by the model layer or by a re-run of the seed import (D43).
"""

from __future__ import annotations

import os
import sqlite3
import time
import urllib.parse
from pathlib import Path

SCHEMA = """
create table if not exists labels (
    id text primary key,
    topic text not null,
    value integer not null check (value between 0 and 3),
    summary text not null,
    source text not null check (source in ('llm', 'manual')),
    updated_at real not null
);
create table if not exists flags (
    id text primary key,
    loose_end_done integer not null default 0,
    updated_at real not null
);
"""


def db_path(home: Path) -> Path:
    return Path(home) / "logbuch" / "labels.db"


def _connect_write(home: Path) -> sqlite3.Connection:
    path = db_path(home)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fresh = not path.exists()
    conn = sqlite3.connect(path, timeout=5.0)
    if fresh:
        os.chmod(path, 0o600)
    conn.executescript(SCHEMA)
    return conn


def _connect_read(home: Path) -> sqlite3.Connection | None:
    path = db_path(home)
    if not path.exists():
        return None
    return sqlite3.connect("file:" + urllib.parse.quote(str(path)) + "?mode=ro", uri=True, timeout=5.0)


def read_all(home: Path) -> tuple[dict[str, dict], set[str]]:
    """({id: {topic, value, summary, source}}, ids with loose_end_done). Empty when labels.db is absent."""
    conn = _connect_read(home)
    if conn is None:
        return {}, set()
    try:
        labels = {
            row[0]: {"topic": row[1], "value": row[2], "summary": row[3], "source": row[4]}
            for row in conn.execute("select id, topic, value, summary, source from labels")
        }
        done = {row[0] for row in conn.execute("select id from flags where loose_end_done = 1")}
        return labels, done
    except sqlite3.OperationalError:
        # A labels.db file without our tables (never written by us): treat as empty, never a 500.
        return {}, set()
    finally:
        conn.close()


def put_manual(home: Path, session_id: str, label: dict | None, loose_end_done: bool | None) -> None:
    """Store a manual label and/or the loose-end flag in one transaction."""
    now = time.time()
    conn = _connect_write(home)
    try:
        with conn:
            if label is not None:
                conn.execute(
                    "insert into labels (id, topic, value, summary, source, updated_at) values (?, ?, ?, ?, 'manual', ?) "
                    "on conflict(id) do update set topic = excluded.topic, value = excluded.value, "
                    "summary = excluded.summary, source = 'manual', updated_at = excluded.updated_at",
                    (session_id, label["topic"], label["value"], label["summary"], now),
                )
            if loose_end_done is not None:
                conn.execute(
                    "insert into flags (id, loose_end_done, updated_at) values (?, ?, ?) "
                    "on conflict(id) do update set loose_end_done = excluded.loose_end_done, updated_at = excluded.updated_at",
                    (session_id, int(loose_end_done), now),
                )
    finally:
        conn.close()


def put_llm(home: Path, session_id: str, topic: str, value: int, summary: str) -> bool:
    """Store a model label unless a manual one exists. True when a row was written."""
    conn = _connect_write(home)
    try:
        with conn:
            cur = conn.execute(
                "insert into labels (id, topic, value, summary, source, updated_at) values (?, ?, ?, ?, 'llm', ?) "
                "on conflict(id) do update set topic = excluded.topic, value = excluded.value, "
                "summary = excluded.summary, source = 'llm', updated_at = excluded.updated_at "
                "where labels.source != 'manual'",
                (session_id, topic, value, summary, time.time()),
            )
        return cur.rowcount > 0
    finally:
        conn.close()


def seed_manual(home: Path, rows: list[tuple[str, str, int, str]]) -> dict:
    """Load (id, topic, value, summary) as manual labels, idempotent.

    An existing manual label is kept as is, so re-running never undoes an edit made in the pane; an llm
    label is replaced (manual outranks it). Returns counts.
    """
    counts = {"rows": len(rows), "inserted": 0, "replaced_llm": 0, "kept_manual": 0}
    now = time.time()
    conn = _connect_write(home)
    try:
        with conn:
            for sid, topic, value, summary in rows:
                prev = conn.execute("select source from labels where id = ?", (sid,)).fetchone()
                if prev is None:
                    counts["inserted"] += 1
                elif prev[0] == "manual":
                    counts["kept_manual"] += 1
                    continue
                else:
                    counts["replaced_llm"] += 1
                conn.execute(
                    "insert into labels (id, topic, value, summary, source, updated_at) values (?, ?, ?, ?, 'manual', ?) "
                    "on conflict(id) do update set topic = excluded.topic, value = excluded.value, "
                    "summary = excluded.summary, source = 'manual', updated_at = excluded.updated_at",
                    (sid, topic, value, summary, now),
                )
        counts["manual_total"] = conn.execute("select count(*) from labels where source = 'manual'").fetchone()[0]
        counts["llm_total"] = conn.execute("select count(*) from labels where source = 'llm'").fetchone()[0]
    finally:
        conn.close()
    return counts
