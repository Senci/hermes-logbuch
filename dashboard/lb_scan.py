"""Aggregate state.db into per-root session items, with a per-root cache.

state.db is opened read-only (mode=ro URI). A root is a desktop or cli session with no parent; its
compression children are folded into it. A root qualifies like in the session-recall prototype
(real-work-sessions.sql): chain tool calls >= 20 and edits + commits + MRs + kanban cards > 0, the same
LIKE patterns. The message scan is the expensive part, so each chain is cached on its signature
(max last activity, tool-call sum, chain size) and a refresh re-reads only chains whose signature moved.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import lb_data
import states as lb_states

log = logging.getLogger("logbuch.scan")

ROOT_SOURCES = ("desktop", "cli")
MIN_TOOL_CALLS = 20
TEXT_KEEP = 4000
# The prototype matches LOOSE on session-digest.sql's reply: first 320 chars, newlines and tabs as spaces.
LOOSE_WINDOW = 320

SESSION_COLUMNS = (
    "id", "source", "parent_session_id", "started_at", "last_activity_at", "ended_at", "title", "cwd",
    "git_repo_root", "message_count", "tool_call_count",
)
MESSAGE_COLUMNS = ("id", "session_id", "role", "content", "tool_calls")

# Verbatim from real-work-sessions.sql so the counts agree row for row.
EDIT_SQL = "tool_calls like '%\"name\": \"write_file\"%' or tool_calls like '%\"name\": \"patch\"%'"
COMMIT_SQL = "tool_calls like '%git commit%'"
MR_SQL = (
    "tool_calls like '%glab mr create%' or tool_calls like '%glab mr merge%' "
    "or tool_calls like '%gh pr create%'"
)
CARD_SQL = "tool_calls like '%\"name\": \"kanban_create\"%'"


def open_readonly(path: Path) -> sqlite3.Connection:
    uri = "file:" + urllib.parse.quote(str(path)) + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5.0)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"pragma table_info({table})")}


@dataclass
class Schema:
    sessions: set = field(default_factory=set)
    messages: set = field(default_factory=set)

    @property
    def ok(self) -> bool:
        return set(SESSION_COLUMNS) <= self.sessions and set(MESSAGE_COLUMNS) <= self.messages

    @property
    def has_signals(self) -> bool:
        return {"session_id", "role", "tool_calls"} <= self.messages

    @property
    def has_text(self) -> bool:
        return {"id", "session_id", "role", "content"} <= self.messages

    @property
    def has_display(self) -> bool:
        return {"id", "session_id", "role", "content", "display_kind", "display_metadata"} <= self.messages

    @property
    def has_turns(self) -> bool:
        return {"session_id", "role"} <= self.messages

    def missing(self) -> list[str]:
        return sorted(
            [f"sessions.{c}" for c in set(SESSION_COLUMNS) - self.sessions]
            + [f"messages.{c}" for c in set(MESSAGE_COLUMNS) - self.messages]
        )


def probe(conn: sqlite3.Connection) -> Schema:
    return Schema(sessions=_columns(conn, "sessions"), messages=_columns(conn, "messages"))


@dataclass
class Entry:
    """Cached, message-derived facts of one chain; valid while the chain signature holds."""

    sig: tuple
    qualifies: bool
    counts: dict = field(default_factory=dict)
    first_prompt: str = ""
    last_reply: str = ""
    facts: lb_states.StateFacts = lb_states.NO_FACTS


@dataclass
class Hit:
    """One qualifying root in a snapshot: session fields read fresh on every refresh, plus the cached facts."""

    item: dict
    cwd: str | None
    git_repo_root: str | None
    first_prompt: str
    last_reply: str
    facts: lb_states.StateFacts = lb_states.NO_FACTS


@dataclass
class Snapshot:
    schema_ok: bool
    entries: list  # Hit objects, started_at desc
    missing: list = field(default_factory=list)


def _clean(text: str | None) -> str:
    return (text or "").replace("\n", " ").replace("\t", " ")


def loose_end(last_reply: str, loose: re.Pattern) -> bool:
    window = _clean(last_reply)[:LOOSE_WINDOW]
    return bool(window) and bool(loose.search(window))


class Scanner:
    """One per state.db path: holds the per-root cache and the refresh counters."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._cache: dict[str, Entry] = {}
        self._data_key: tuple | None = None
        self._snapshot: Snapshot | None = None
        self.chains_scanned_total = 0
        self.last_stats: dict = {}

    def refresh(self, data: lb_data.Data) -> Snapshot:
        with self._lock:
            started = time.perf_counter()
            if data.key != self._data_key:
                self._cache.clear()  # the cached facts were matched with the old open_states
                self._data_key = data.key
            try:
                snap, scanned, roots = self._refresh_locked(data)
            except (sqlite3.Error, OSError) as exc:
                log.warning("logbuch: state.db read failed (%s): %s", self.db_path, exc)
                if self._snapshot is not None:
                    return self._snapshot
                self._snapshot = Snapshot(schema_ok=False, entries=[], missing=["state.db unreadable"])
                return self._snapshot
            ms = (time.perf_counter() - started) * 1000
            self.chains_scanned_total += scanned
            self.last_stats = {"roots": roots, "scanned": scanned, "qualifying": len(snap.entries), "ms": round(ms, 1)}
            log.info("logbuch scan roots=%d chains_rescanned=%d qualifying=%d ms=%.0f", roots, scanned, len(snap.entries), ms)
            self._snapshot = snap
            return snap

    def _refresh_locked(self, data: lb_data.Data) -> tuple[Snapshot, int, int]:
        if not self.db_path.exists():
            self._cache.clear()
            return Snapshot(schema_ok=False, entries=[], missing=["state.db missing"]), 0, 0
        conn = open_readonly(self.db_path)
        try:
            schema = probe(conn)
            if not schema.sessions:
                self._cache.clear()
                return Snapshot(schema_ok=False, entries=[], missing=["sessions table"]), 0, 0
            rows = self._session_rows(conn, schema)
            chains = _fold_chains(rows)
            scanned = 0
            live: set[str] = set()
            hits: list[Hit] = []
            for root_id, chain in chains.items():
                live.add(root_id)
                sig = _signature(chain)
                cached = self._cache.get(root_id)
                if cached is None or cached.sig != sig:
                    cached = self._scan_chain(conn, schema, chain, sig, data)
                    self._cache[root_id] = cached
                    scanned += 1
                if cached.qualifies:
                    hits.append(_hit(chain[0], sig, cached, data.loose))
            for gone in set(self._cache) - live:
                del self._cache[gone]
            hits.sort(key=lambda h: h.item["started_at"], reverse=True)
            return Snapshot(schema_ok=schema.ok, entries=hits, missing=schema.missing()), scanned, len(chains)
        finally:
            conn.close()

    @staticmethod
    def _session_rows(conn: sqlite3.Connection, schema: Schema) -> list[dict]:
        cols = ", ".join(c if c in schema.sessions else f"null as {c}" for c in SESSION_COLUMNS)
        cur = conn.execute(f"select {cols} from sessions")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row)) for row in cur]

    def _scan_chain(
        self, conn: sqlite3.Connection, schema: Schema, chain: list[dict], sig: tuple, data: lb_data.Data
    ) -> Entry:
        if sig[1] < MIN_TOOL_CALLS:
            return Entry(sig=sig, qualifies=False)
        ids = [s["id"] for s in chain]
        counts = _message_counts(conn, schema, ids, chain)
        shipped = counts["edits"] + counts["commits"] + counts["mrs"] + counts["cards"]
        # Without messages.tool_calls the signals are unknowable: session-level counts qualify on tool calls alone.
        if schema.has_signals and shipped == 0:
            return Entry(sig=sig, qualifies=False)
        first_prompt, last_reply = _digest_text(conn, schema, ids)
        facts = lb_states.analyze(last_reply, _last_message(conn, schema, ids), LOOSE_WINDOW, data.open_patterns)
        return Entry(
            sig=sig, qualifies=True, counts=counts, first_prompt=first_prompt, last_reply=last_reply, facts=facts
        )


def _hit(root: dict, sig: tuple, entry: Entry, loose: re.Pattern) -> Hit:
    counts = entry.counts
    item = {
        "id": root["id"],
        "title": _clean(root["title"]) if root["title"] else "(untitled)",
        "started_at": root["started_at"],
        "last_active_at": sig[0],
        "turns": counts["turns"],
        "tool_calls": sig[1],
        "edits": counts["edits"],
        "commit_calls": counts["commits"],
        "mr_calls": counts["mrs"],
        "loose_end": loose_end(entry.last_reply, loose),
    }
    return Hit(item, root["cwd"], root["git_repo_root"], entry.first_prompt, entry.last_reply, entry.facts)


def _fold_chains(rows: list[dict]) -> dict[str, list[dict]]:
    """Root id -> [root, children...]; a root is a desktop or cli session without a parent."""
    children: dict[str, list[dict]] = {}
    for row in rows:
        if row["parent_session_id"] is not None:
            children.setdefault(row["parent_session_id"], []).append(row)
    chains: dict[str, list[dict]] = {}
    for row in rows:
        if row["parent_session_id"] is not None or row["source"] not in ROOT_SOURCES:
            continue
        chain, seen, queue = [], {row["id"]}, [row]
        while queue:
            cur = queue.pop(0)
            chain.append(cur)
            for kid in children.get(cur["id"], []):
                if kid["id"] not in seen:
                    seen.add(kid["id"])
                    queue.append(kid)
        chains[row["id"]] = chain
    return chains


def _signature(chain: list[dict]) -> tuple:
    """(max last activity, tool-call sum, chain size): moves when a chain gains messages or a child."""
    last = max(
        (s["last_activity_at"] if s["last_activity_at"] is not None
         else s["ended_at"] if s["ended_at"] is not None else s["started_at"])
        for s in chain
    )
    return (last, sum(s["tool_call_count"] or 0 for s in chain), len(chain))


def _message_counts(conn: sqlite3.Connection, schema: Schema, ids: list[str], chain: list[dict]) -> dict:
    out = {"turns": 0, "edits": 0, "commits": 0, "mrs": 0, "cards": 0}
    if not schema.has_turns:
        out["turns"] = sum(s["message_count"] or 0 for s in chain)
        return out
    marks = ",".join("?" * len(ids))
    if schema.has_signals:
        sql = (
            f"select coalesce(sum(role = 'user'), 0), coalesce(sum({EDIT_SQL}), 0), "
            f"coalesce(sum({COMMIT_SQL}), 0), coalesce(sum({MR_SQL}), 0), coalesce(sum({CARD_SQL}), 0) "
            f"from messages where session_id in ({marks})"
        )
    else:
        sql = f"select coalesce(sum(role = 'user'), 0), 0, 0, 0, 0 from messages where session_id in ({marks})"
    row = conn.execute(sql, ids).fetchone()
    out.update(zip(("turns", "edits", "commits", "mrs", "cards"), (int(v) for v in row)))
    return out


def _digest_text(conn: sqlite3.Connection, schema: Schema, ids: list[str]) -> tuple[str, str]:
    """First user prompt (>3 chars) and last assistant reply (>40 chars) across the chain, as session-digest.sql."""
    if not schema.has_text:
        return "", ""
    first: tuple[int, str] | None = None
    last: tuple[int, str] | None = None
    for sid in ids:
        row = conn.execute(
            "select id, substr(content, 1, ?) from messages where session_id = ? and role = 'user' "
            "and length(content) > 3 order by id limit 1", (TEXT_KEEP, sid),
        ).fetchone()
        if row and (first is None or row[0] < first[0]):
            first = row
        row = conn.execute(
            "select id, substr(content, 1, ?) from messages where session_id = ? and role = 'assistant' "
            "and length(content) > 40 order by id desc limit 1", (TEXT_KEEP, sid),
        ).fetchone()
        if row and (last is None or row[0] > last[0]):
            last = row
    return (first[1] if first else ""), (last[1] if last else "")


def _last_message(conn: sqlite3.Connection, schema: Schema, ids: list[str]) -> dict | None:
    """The chain's last assistant message of any length that is a reply or a failed turn.

    Skips tool-call-only rows (empty content) and the `hidden` UI marker rows. The display columns are
    optional: without them a message is just its content, so only the interrupt lines can match.
    """
    if not schema.has_text:
        return None
    kind_sql = "display_kind, display_metadata" if schema.has_display else "null, null"
    skip = "and coalesce(display_kind, '') != 'hidden' " if schema.has_display else ""
    reply = "(length(content) > 0 or display_kind = 'failed_turn')" if schema.has_display else "length(content) > 0"
    best: tuple | None = None
    for sid in ids:
        row = conn.execute(
            f"select id, substr(content, 1, ?), {kind_sql} from messages where session_id = ? "
            f"and role = 'assistant' {skip}and {reply} order by id desc limit 1", (TEXT_KEEP, sid),
        ).fetchone()
        if row and (best is None or row[0] > best[0]):
            best = row
    if best is None:
        return None
    return {"content": best[1], "display_kind": best[2], "display_metadata": best[3]}


_scanners: dict[str, Scanner] = {}
_scanners_lock = threading.Lock()


def scanner_for(db_path: Path) -> Scanner:
    key = str(Path(db_path).resolve())
    with _scanners_lock:
        if key not in _scanners:
            _scanners[key] = Scanner(Path(key))
        return _scanners[key]
