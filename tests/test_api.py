"""Route-level tests: /sessions, PUT /labels/{id}, /digest, /digest/file, and the two W3 hooks.

The handlers are called as plain functions with HERMES_HOME pointed at a temp home, which is what the
dashboard's request path resolves to. No live paths.
"""

from __future__ import annotations

import os
import sqlite3
import stat
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import support
from support import add_message, add_session, raw_calls

api = support.load_api()
HTTPException = sys.modules["fastapi"].HTTPException
svc = sys.modules["lb_service"]


def local_epoch(y, m, d, h=12) -> float:
    return time.mktime(datetime(y, m, d, h).timetuple())


class ApiCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        data_file = support.write_data(Path(self._tmp.name) / "data.json")
        support.use_settings(self, data_file=str(data_file))
        conn = support.build_world(self.home / "state.db")
        add_session(conn, "Q", "cli", started=2000, last=2100, tool_calls=30, title="Billing rights",
                    cwd="/home/u/src/billing")
        add_message(conn, "Q", "user", "fix the billing export")
        add_message(conn, "Q", "assistant", "", raw_calls("patch"))
        add_session(conn, "N", "cli", started=1500, last=1600, tool_calls=30, title="Flow", cwd="/home/u/src/sync")
        add_message(conn, "N", "user", "adjust the sync flow")
        add_message(conn, "N", "assistant", "", raw_calls("write_file"))
        conn.commit()
        conn.close()
        patcher = mock.patch.dict(os.environ, {"HERMES_HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def sessions(self) -> dict:
        return {i["id"]: i for i in api.sessions()["items"]}

    def labels_db(self) -> Path:
        return self.home / "logbuch" / "labels.db"

    def put(self, sid, body):
        return api.put_label(sid, body)

    def assert_http(self, status, fn, *args):
        with self.assertRaises(HTTPException) as ctx:
            fn(*args)
        self.assertEqual(ctx.exception.status_code, status)
        return ctx.exception


class TestSessionsRoute(ApiCase):
    def test_payload_shape(self):
        out = api.sessions()
        self.assertEqual(sorted(out), ["generated_at", "items", "profile", "schema_ok", "topics"])
        self.assertTrue(out["schema_ok"])
        self.assertEqual(out["topics"], support.TEST_RAW["topics"])
        self.assertIsInstance(out["generated_at"], float)
        self.assertTrue(out["profile"])
        self.assertEqual([i["id"] for i in out["items"]], ["Q", "N", "C", "A"])
        item = out["items"][3]
        self.assertEqual(
            sorted(item),
            ["commit_calls", "edits", "id", "label", "last_active_at", "loose_end", "loose_end_done",
             "mr_calls", "started_at", "state", "state_evidence", "title", "tool_calls", "turns"],
        )

    def test_rule_label_for_a_known_repo_path(self):
        label = self.sessions()["Q"]["label"]
        self.assertEqual(label, {"topic": "BILL", "value": 3, "summary": "Billing rights", "source": "rule"})

    def test_topic_only_rule_is_a_hint_not_a_label(self):
        self.assertIsNone(self.sessions()["N"]["label"])

    def test_reading_never_creates_labels_db_or_the_logbuch_dir(self):
        api.sessions()
        api.digest("2026-W43")
        svc.unlabelled_items(self.home)
        self.assertFalse(self.labels_db().exists())
        self.assertFalse((self.home / "logbuch").exists())

    def test_bad_state_db_answers_200_with_schema_ok_false(self):
        (self.home / "state.db").write_bytes(b"junk" * 1000)
        with self.assertLogs("logbuch.scan", "WARNING"):
            out = api.sessions()
        self.assertFalse(out["schema_ok"])
        self.assertEqual(out["items"], [])

    def test_schema_probe_through_the_route(self):
        for kw in ({"drop_message": ("tool_calls",)}, {"drop_session": ("last_activity_at",)}):
            with self.subTest(**kw), tempfile.TemporaryDirectory() as tmp:
                support.build_world(Path(tmp) / "state.db", **kw).close()
                with mock.patch.dict(os.environ, {"HERMES_HOME": tmp}):
                    out = api.sessions()
                self.assertFalse(out["schema_ok"])
                self.assertTrue(out["items"])

    def test_state_db_stays_byte_identical_through_every_route(self):
        before = (self.home / "state.db").read_bytes()
        api.sessions()
        self.put("A", {"topic": "OPS", "value": 1})
        api.digest("2026-W43")
        api.digest_file({"week": "2026-W43"})
        self.assertEqual((self.home / "state.db").read_bytes(), before)


class TestPutLabel(ApiCase):
    def test_first_label_needs_topic_and_value_and_defaults_summary_to_title(self):
        out = self.put("A", {"topic": "OPS", "value": 2})
        self.assertEqual(out["label"], {"topic": "OPS", "value": 2, "summary": "Alpha work", "source": "manual"})
        self.assertEqual(self.sessions()["A"]["label"], out["label"])

    def test_labels_db_is_created_on_the_first_write_with_private_modes(self):
        self.assertFalse(self.labels_db().exists())
        self.put("A", {"topic": "OPS", "value": 2})
        self.assertTrue(self.labels_db().exists())
        self.assertEqual(stat.S_IMODE(self.labels_db().stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.labels_db().parent.stat().st_mode), 0o700)

    def test_fields_merge_over_the_existing_label(self):
        self.put("A", {"topic": "OPS", "value": 2})
        out = self.put("A", {"summary": "  Fixed   the\tthing  "})
        self.assertEqual(out["label"], {"topic": "OPS", "value": 2, "summary": "Fixed the thing", "source": "manual"})
        out = self.put("A", {"value": 3})
        self.assertEqual((out["label"]["topic"], out["label"]["value"], out["label"]["summary"]), ("OPS", 3, "Fixed the thing"))

    def test_merge_over_a_rule_label_keeps_the_rest_and_flips_source(self):
        out = self.put("Q", {"value": 2})
        self.assertEqual(out["label"], {"topic": "BILL", "value": 2, "summary": "Billing rights", "source": "manual"})

    def test_summary_is_cut_to_120_chars(self):
        out = self.put("A", {"topic": "OPS", "value": 1, "summary": "x" * 300})
        self.assertEqual(out["label"]["summary"], "x" * 120)

    def test_invalid_bodies_are_422_and_write_nothing(self):
        bad = [
            ("A", {"topic": "NOPE", "value": 1}),
            ("A", {"topic": "OPS", "value": 4}),
            ("A", {"topic": "OPS", "value": -1}),
            ("A", {"topic": "OPS", "value": "2"}),
            ("A", {"topic": "OPS", "value": 2.0}),
            ("A", {"topic": "OPS", "value": True}),
            ("A", {"topic": "OPS", "value": 1, "summary": 5}),
            ("A", {"topic": "OPS", "value": 1, "summary": "   "}),
            ("A", {"topic": "OPS", "value": 1, "loose_end_done": "yes"}),
            ("A", {"topic": "OPS", "value": 1, "extra": 1}),
            ("A", {"value": 2}),  # no label yet: topic missing
            ("A", {"summary": "only a summary"}),
            ("A", {}),
            ("A", ["not", "an", "object"]),
        ]
        for sid, body in bad:
            with self.subTest(body=body):
                self.assert_http(422, self.put, sid, body)
        self.assertFalse(self.labels_db().exists())

    def test_unknown_or_non_qualifying_id_is_404(self):
        self.assert_http(404, self.put, "nope", {"topic": "OPS", "value": 1})
        self.assert_http(404, self.put, "B", {"topic": "OPS", "value": 1})  # reads only, not an item

    def test_loose_end_done_alone_changes_only_the_flag(self):
        self.put("A", {"topic": "OPS", "value": 2, "summary": "kept"})
        out = self.put("A", {"loose_end_done": True})
        self.assertTrue(out["loose_end_done"])
        self.assertEqual(out["label"], {"topic": "OPS", "value": 2, "summary": "kept", "source": "manual"})
        self.assertFalse(self.put("A", {"loose_end_done": False})["loose_end_done"])

    def test_loose_end_done_on_an_unlabelled_item_stores_no_label(self):
        out = self.put("C", {"loose_end_done": True})
        self.assertTrue(out["loose_end_done"])
        self.assertIsNone(out["label"])
        conn = sqlite3.connect(self.labels_db())
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("select count(*) from labels").fetchone()[0], 0)

    def test_loose_end_done_is_independent_of_the_label_source(self):
        self.put("A", {"loose_end_done": True})
        self.assertTrue(self.sessions()["A"]["loose_end_done"])
        self.assertTrue(self.sessions()["A"]["loose_end"])  # the regex hit stays, the mark is separate

    def test_label_and_flag_in_one_body(self):
        out = self.put("A", {"topic": "GIT", "value": 1, "loose_end_done": True})
        self.assertEqual((out["label"]["topic"], out["loose_end_done"]), ("GIT", True))


class TestPrecedence(ApiCase):
    def test_llm_label_replaces_a_rule_label_and_is_replaced_by_manual(self):
        self.assertTrue(svc.store_llm_label(self.home, "Q", "OPS", 1, "model view"))
        self.assertEqual(self.sessions()["Q"]["label"]["source"], "llm")
        self.put("Q", {"value": 3})
        self.assertEqual(self.sessions()["Q"]["label"]["source"], "manual")

    def test_a_manual_label_is_never_overwritten_by_the_model(self):
        self.put("A", {"topic": "OPS", "value": 3, "summary": "mine"})
        self.assertFalse(svc.store_llm_label(self.home, "A", "GIT", 0, "model view"))
        self.assertEqual(self.sessions()["A"]["label"], {"topic": "OPS", "value": 3, "summary": "mine", "source": "manual"})

    def test_a_second_llm_label_replaces_the_first(self):
        svc.store_llm_label(self.home, "A", "OPS", 1, "first")
        self.assertTrue(svc.store_llm_label(self.home, "A", "GIT", 2, "second"))
        self.assertEqual(self.sessions()["A"]["label"], {"topic": "GIT", "value": 2, "summary": "second", "source": "llm"})

    def test_invalid_model_output_is_refused_without_a_write(self):
        for args in (("NOPE", 1, "s"), ("OPS", 4, "s"), ("OPS", True, "s"), ("OPS", 1, ""), ("OPS", 1, None)):
            with self.subTest(args=args):
                self.assertFalse(svc.store_llm_label(self.home, "A", *args))
        self.assertFalse(self.labels_db().exists())


class TestW3Hooks(ApiCase):
    def test_unlabelled_items_carry_prompt_reply_and_hint(self):
        rows = {r["id"]: r for r in svc.unlabelled_items(self.home)}
        self.assertEqual(sorted(rows), ["A", "C", "N"])  # Q has a rule label
        self.assertEqual(sorted(rows["A"]), ["first_prompt", "id", "last_reply", "title", "topic_hint"])
        self.assertEqual(rows["A"]["first_prompt"], "start the task please")
        self.assertIn("needs your go", rows["A"]["last_reply"])
        self.assertIsNone(rows["A"]["topic_hint"])
        self.assertEqual(rows["N"]["topic_hint"], "SYNC")

    def test_labelled_items_drop_out_and_limit_applies(self):
        self.put("A", {"topic": "OPS", "value": 1})
        self.assertEqual(sorted(r["id"] for r in svc.unlabelled_items(self.home)), ["C", "N"])
        self.assertEqual(len(svc.unlabelled_items(self.home, limit=1)), 1)


class TestDigestRoutes(ApiCase):
    def setUp(self):
        super().setUp()
        conn = sqlite3.connect(self.home / "state.db")
        conn.execute("update sessions set started_at = ? where id = 'A'", (local_epoch(2026, 10, 20),))  # W43
        conn.execute("update sessions set started_at = ? where id = 'C'", (local_epoch(2026, 10, 27),))  # W44
        conn.execute("update sessions set started_at = ? where id = 'Q'", (local_epoch(2026, 10, 21),))  # W43
        conn.commit()
        conn.close()
        self.put("A", {"topic": "OPS", "value": 2, "summary": "Fixed the ingress"})
        self.put("C", {"topic": "GIT", "value": 3, "summary": "Other week"})

    def test_week_grouping_and_content(self):
        resp = api.digest("2026-W43")
        self.assertEqual(resp.media_type, "text/markdown")
        text = resp.body.decode()
        self.assertIn("# Logbuch 2026-W43", text)
        self.assertIn("## Billing (BILL)", text)
        self.assertIn("## Infra ops (OPS)", text)
        self.assertIn("P2 2026-10-20 Fixed the ingress [commit calls 1, MR calls 2] (loose end open)", text)
        self.assertIn("P1 2026-10-21 Billing rights [commit calls 0, MR calls 0]", text)
        self.assertNotIn("Other week", text)
        self.assertIn("P1: 1, P2: 1, commit calls: 1, MR calls: 2.", text)
        self.assertLess(text.index("(BILL)"), text.index("(OPS)"))  # data file order, not alphabetical

    def test_other_week_and_empty_week(self):
        self.assertIn("Other week", api.digest("2026-W44").body.decode())
        self.assertIn("No P1 or P2 sessions", api.digest("2026-W20").body.decode())

    def test_value_below_p2_is_left_out(self):
        self.put("A", {"value": 1})
        self.assertNotIn("Fixed the ingress", api.digest("2026-W43").body.decode())

    def test_missing_week_means_the_current_week(self):
        self.assertIn("# Logbuch 20", api.digest(None).body.decode())

    def test_bad_week_is_400(self):
        for week in ("2026-43", "26-W43", "2026-W00", "2026-W54", "2025-W53", "", "2026-W4", "x", "../../etc"):
            with self.subTest(week=week):
                self.assert_http(400, api.digest, week)

    def test_digest_file_path_and_content(self):
        out = api.digest_file({"week": "2026-W43"})
        want = self.home / "logbuch" / "digests" / "logbuch-2026-W43.md"
        self.assertEqual(out, {"path": str(want), "name": "logbuch-2026-W43.md"})
        self.assertEqual(want.read_text(encoding="utf-8"), api.digest("2026-W43").body.decode())

    def test_digest_file_is_overwritten_not_duplicated(self):
        api.digest_file({"week": "2026-W43"})
        self.put("A", {"summary": "Changed"})
        api.digest_file({"week": "2026-W43"})
        files = list((self.home / "logbuch" / "digests").iterdir())
        self.assertEqual([f.name for f in files], ["logbuch-2026-W43.md"])
        self.assertIn("Changed", files[0].read_text(encoding="utf-8"))

    def test_digest_file_rejects_bad_weeks_and_path_tricks(self):
        for body in ({"week": "../x"}, {"week": "2026-W99"}, {"week": 5}, {}, {"week": None}):
            with self.subTest(body=body):
                self.assert_http(400, api.digest_file, body)
        self.assertFalse((self.home / "logbuch" / "digests").exists())


class TestDataFileThroughTheRoutes(ApiCase):
    def write(self, **changes):
        support.write_data(self.data_path, dict(support.TEST_RAW, **changes))

    @property
    def data_path(self) -> Path:
        return self.home / "data.json"

    def test_a_bad_file_answers_200_with_the_neutral_default(self):
        self.data_path.write_text("{ not json", encoding="utf-8")
        with self.assertLogs("logbuch.data", "ERROR"):
            out = api.sessions()
        self.assertTrue(out["schema_ok"])
        self.assertEqual(out["topics"], support.lb_data.DEFAULT.topics)
        self.assertIsNone({i["id"]: i for i in out["items"]}["Q"]["label"])  # the rule is gone with the file

    def test_no_file_at_all_gives_the_neutral_topics_and_no_rule_labels(self):
        self.data_path.unlink()
        support.use_settings(self, data_file="")
        out = api.sessions()
        self.assertTrue(out["schema_ok"])
        self.assertEqual(out["topics"], support.lb_data.DEFAULT.topics)
        self.assertTrue(all(i["label"] is None for i in out["items"]))
        self.assertEqual(self.put("A", {"topic": "BUILD", "value": 2})["label"]["topic"], "BUILD")

    def test_label_validation_and_the_error_text_follow_the_loaded_topics(self):
        self.write(topics={"ONLY": "The only topic"}, rules=[])
        self.assertEqual(api.sessions()["topics"], {"ONLY": "The only topic"})
        err = self.assert_http(422, self.put, "A", {"topic": "OPS", "value": 1})
        self.assertEqual(err.detail, "topic must be one of ONLY")
        self.assertEqual(self.put("A", {"topic": "ONLY", "value": 1})["label"]["topic"], "ONLY")
        self.assertFalse(svc.store_llm_label(self.home, "C", "OPS", 1, "s"))
        self.assertTrue(svc.store_llm_label(self.home, "C", "ONLY", 1, "s"))

    def test_open_state_phrases_follow_the_file_without_a_restart(self):
        self.assertEqual(self.sessions()["A"]["state"], "waiting_go")
        self.write(open_states={"todo": "still open"})
        item = self.sessions()["A"]
        self.assertEqual(item["state"], "todo")
        self.assertIn("still open", item["state_evidence"])

    def test_the_loose_end_flag_follows_the_file(self):
        self.assertTrue(self.sessions()["A"]["loose_end"])
        self.write(loose_end="zzz never matches")
        self.assertFalse(self.sessions()["A"]["loose_end"])

    def test_rules_follow_the_file(self):
        self.write(rules=[])
        self.assertIsNone(self.sessions()["Q"]["label"])
        rule = {"name": "path:any", "field": "path", "pattern": "/src/", "topic": "WS", "value": 1}
        self.write(rules=[rule])
        self.assertEqual(self.sessions()["Q"]["label"]["topic"], "WS")


if __name__ == "__main__":
    unittest.main()
