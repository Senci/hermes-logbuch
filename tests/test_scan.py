"""Aggregation, chain fold, cache invalidation, schema fallback and read-only access of lb_scan."""

from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support
from support import add_message, add_session, raw_calls

sys.path.insert(0, str(support.DASHBOARD))
import lb_scan  # noqa: E402


build = support.build_world


class ScanCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Path(self._tmp.name) / "state.db"
        self.conn = build(self.db)
        self.addCleanup(self.conn.close)
        self.scanner = lb_scan.Scanner(self.db)

    def items(self):
        return {e.item["id"]: e.item for e in self.scanner.refresh(support.DATA).entries}


class TestAggregation(ScanCase):
    def test_qualifying_roots_only(self):
        self.assertEqual(sorted(self.items()), ["A", "C"])

    def test_chain_fold_counts(self):
        a = self.items()["A"]
        self.assertEqual(
            (a["turns"], a["tool_calls"], a["edits"], a["commit_calls"], a["mr_calls"]), (3, 25, 3, 1, 2)
        )

    def test_chain_last_activity_is_the_max_over_the_chain(self):
        self.assertEqual(self.items()["A"]["last_active_at"], 9000)

    def test_last_activity_falls_back_to_ended_at(self):
        self.assertEqual(self.items()["C"]["last_active_at"], 7000)

    def test_cards_alone_qualify_but_are_not_an_item_field(self):
        c = self.items()["C"]
        self.assertEqual((c["edits"], c["commit_calls"], c["mr_calls"]), (0, 0, 0))
        self.assertNotIn("cards", c)

    def test_title_newline_and_untitled(self):
        items = self.items()
        self.assertEqual(items["A"]["title"], "Alpha work")
        self.assertEqual(items["C"]["title"], "(untitled)")

    def test_sorted_by_started_at_desc(self):
        order = [e.item["id"] for e in self.scanner.refresh(support.DATA).entries]
        self.assertEqual(order, ["C", "A"])

    def test_kanban_oneshot_and_small_roots_never_appear(self):
        for sid in ("B", "D", "E", "G", "A2"):
            self.assertNotIn(sid, self.items())

    def test_loose_end_from_last_assistant_reply_across_the_chain(self):
        self.assertTrue(self.items()["A"]["loose_end"])
        self.assertFalse(self.items()["C"]["loose_end"])

    def test_short_final_reply_is_skipped_for_the_loose_end_scan(self):
        add_message(self.conn, "A2", "assistant", "ok")
        self.conn.execute("update sessions set last_activity_at = 9100 where id = 'A2'")
        self.conn.commit()
        self.assertEqual(self.scanner.refresh(support.DATA).entries[1].last_reply[:4], "Done")

    def test_loose_phrase_past_the_digest_window_does_not_count(self):
        self.assertFalse(lb_scan.loose_end("x" * 330 + " needs your go", support.DATA.loose))
        self.assertTrue(lb_scan.loose_end("Done.\nneeds your go", support.DATA.loose))

    def test_first_prompt_and_last_reply_for_the_model_layer(self):
        entry = self.scanner.refresh(support.DATA).entries[1]
        self.assertEqual(entry.first_prompt, "start the task please")
        self.assertIn("needs your go", entry.last_reply)

    def test_schema_ok_on_the_full_schema(self):
        snap = self.scanner.refresh(support.DATA)
        self.assertTrue(snap.schema_ok)
        self.assertEqual(snap.missing, [])


class TestCache(ScanCase):
    def test_cold_scans_every_candidate_then_warm_scans_none(self):
        self.scanner.refresh(support.DATA)
        # roots: A, B, C, D (E and G are not roots)
        self.assertEqual(self.scanner.last_stats["roots"], 4)
        self.assertEqual(self.scanner.last_stats["scanned"], 4)
        self.scanner.refresh(support.DATA)
        self.assertEqual(self.scanner.last_stats["scanned"], 0)
        self.assertEqual(self.scanner.chains_scanned_total, 4)

    def test_a_changed_chain_is_the_only_one_rescanned(self):
        self.scanner.refresh(support.DATA)
        add_message(self.conn, "A2", "user", "one more turn")
        self.conn.execute("update sessions set last_activity_at = 9500 where id = 'A2'")
        self.conn.commit()
        snap = self.scanner.refresh(support.DATA)
        self.assertEqual(self.scanner.last_stats["scanned"], 1)
        a = next(e.item for e in snap.entries if e.item["id"] == "A")
        self.assertEqual((a["turns"], a["last_active_at"]), (4, 9500))

    def test_a_new_child_changes_the_chain_signature(self):
        self.scanner.refresh(support.DATA)
        add_session(self.conn, "A3", "desktop", parent="A2", started=300, last=5000, tool_calls=0)
        add_message(self.conn, "A3", "user", "child turn")
        self.conn.commit()
        self.scanner.refresh(support.DATA)
        self.assertEqual(self.scanner.last_stats["scanned"], 1)
        self.assertEqual(self.items()["A"]["turns"], 4)

    def test_a_rename_shows_at_once_without_a_rescan(self):
        self.scanner.refresh(support.DATA)
        self.conn.execute("update sessions set title = 'Renamed' where id = 'A'")
        self.conn.commit()
        self.assertEqual(self.items()["A"]["title"], "Renamed")
        self.assertEqual(self.scanner.last_stats["scanned"], 0)

    def test_a_deleted_root_leaves_the_cache_and_the_items(self):
        self.scanner.refresh(support.DATA)
        self.conn.execute("delete from sessions where id = 'C'")
        self.conn.commit()
        self.assertEqual(sorted(self.items()), ["A"])
        self.assertNotIn("C", self.scanner._cache)

    def test_a_chain_that_starts_qualifying_is_picked_up(self):
        self.scanner.refresh(support.DATA)
        add_message(self.conn, "B", "assistant", "", raw_calls("patch"))
        self.conn.execute("update sessions set last_activity_at = 450 where id = 'B'")
        self.conn.commit()
        self.assertIn("B", self.items())


class TestSchemaFallback(unittest.TestCase):
    def run_case(self, **drop):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "state.db"
        conn = build(db, **drop)
        self.addCleanup(conn.close)
        return lb_scan.Scanner(db).refresh(support.DATA)

    def test_without_messages_tool_calls_falls_back_to_session_level_counts(self):
        snap = self.run_case(drop_message=("tool_calls",))
        self.assertFalse(snap.schema_ok)
        self.assertIn("messages.tool_calls", snap.missing)
        items = {e.item["id"]: e.item for e in snap.entries}
        self.assertEqual(sorted(items), ["A", "B", "C"])  # tool calls >= 20, signals unknowable
        self.assertEqual((items["A"]["edits"], items["A"]["commit_calls"], items["A"]["mr_calls"]), (0, 0, 0))
        self.assertEqual((items["A"]["turns"], items["A"]["tool_calls"]), (3, 25))

    def test_without_last_activity_at_uses_ended_at_then_started_at(self):
        snap = self.run_case(drop_session=("last_activity_at",))
        self.assertFalse(snap.schema_ok)
        self.assertEqual(snap.missing, ["sessions.last_activity_at"])
        items = {e.item["id"]: e.item for e in snap.entries}
        self.assertEqual(sorted(items), ["A", "C"])
        self.assertEqual(items["A"]["last_active_at"], 200)  # max started_at over the chain
        self.assertEqual(items["C"]["last_active_at"], 7000)

    def test_without_the_messages_table_columns_turns_use_message_count(self):
        snap = self.run_case(drop_message=("role", "tool_calls"))
        self.assertFalse(snap.schema_ok)
        self.assertTrue(snap.entries)

    def test_missing_db_file_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap = lb_scan.Scanner(Path(tmp) / "state.db").refresh(support.DATA)
        self.assertFalse(snap.schema_ok)
        self.assertEqual(snap.entries, [])

    def test_a_file_that_is_not_sqlite_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.db"
            db.write_bytes(b"not a database" * 100)
            with self.assertLogs("logbuch.scan", "WARNING"):
                snap = lb_scan.Scanner(db).refresh(support.DATA)
        self.assertFalse(snap.schema_ok)
        self.assertEqual(snap.entries, [])

    def test_a_read_error_after_a_good_scan_serves_the_last_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.db"
            conn = build(db)
            conn.close()
            scanner = lb_scan.Scanner(db)
            good = scanner.refresh(support.DATA)
            db.write_bytes(b"garbage" * 1000)
            with self.assertLogs("logbuch.scan", "WARNING"):
                self.assertIs(scanner.refresh(support.DATA), good)


class TestReadOnly(ScanCase):
    def test_every_scanner_connection_is_a_mode_ro_uri(self):
        real = sqlite3.connect
        calls = []

        def spy(*args, **kw):
            calls.append((args, kw))
            return real(*args, **kw)

        with mock.patch.object(lb_scan.sqlite3, "connect", spy):
            self.scanner.refresh(support.DATA)
        self.assertTrue(calls)
        for args, kw in calls:
            self.assertIn("mode=ro", args[0])
            self.assertTrue(kw.get("uri"))

    def test_a_write_through_the_scanner_connection_fails(self):
        conn = lb_scan.open_readonly(self.db)
        self.addCleanup(conn.close)
        with self.assertRaises(sqlite3.OperationalError) as ctx:
            conn.execute("update sessions set title = 'x'")
        self.assertIn("readonly", str(ctx.exception))
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("create table x (a)")

    def test_refresh_leaves_state_db_bytes_untouched(self):
        self.conn.commit()
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.scanner.refresh(support.DATA)
        self.scanner.refresh(support.DATA)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_path_with_a_question_mark_still_opens_read_only(self):
        odd = self.db.with_name("odd?name#1.db")
        odd.write_bytes(self.db.read_bytes())
        conn = lb_scan.open_readonly(odd)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("select count(*) from sessions").fetchone()[0], 7)


if __name__ == "__main__":
    unittest.main()
