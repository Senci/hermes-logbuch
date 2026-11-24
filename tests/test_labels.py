"""Label store and seed import: manual precedence, idempotence, no write on read, live-home refusal."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import support

sys.path.insert(0, str(support.DASHBOARD))
import lb_labels  # noqa: E402

SEED = support.PLUGIN / "scripts" / "seed_import.py"
TSV = "s1\tOPS\t2\tProxy audit\ns2\tBUILD\t3\tShipped the crew MR\ns3\tPERSONAL\t0\tPersonal\n"


class LabelStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_read_of_a_missing_store_creates_nothing(self):
        self.assertEqual(lb_labels.read_all(self.home), ({}, set()))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_read_of_a_foreign_sqlite_file_is_empty_not_an_error(self):
        path = lb_labels.db_path(self.home)
        path.parent.mkdir()
        sqlite3.connect(path).close()
        self.assertEqual(lb_labels.read_all(self.home), ({}, set()))

    def test_the_read_connection_cannot_write(self):
        lb_labels.put_llm(self.home, "s1", "OPS", 1, "x")
        conn = lb_labels._connect_read(self.home)
        self.addCleanup(conn.close)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("delete from labels")

    def test_manual_beats_llm_and_llm_does_not_beat_manual(self):
        self.assertTrue(lb_labels.put_llm(self.home, "s1", "OPS", 1, "model"))
        lb_labels.put_manual(self.home, "s1", {"topic": "GIT", "value": 2, "summary": "me"}, None)
        self.assertFalse(lb_labels.put_llm(self.home, "s1", "OPS", 0, "model again"))
        labels, _ = lb_labels.read_all(self.home)
        self.assertEqual(labels["s1"], {"topic": "GIT", "value": 2, "summary": "me", "source": "manual"})

    def test_flag_only_write_leaves_labels_alone(self):
        lb_labels.put_manual(self.home, "s1", None, True)
        labels, done = lb_labels.read_all(self.home)
        self.assertEqual((labels, done), ({}, {"s1"}))


class SeedImport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.tsv = self.root / "labels.tsv"
        self.tsv.write_text(TSV, encoding="utf-8")
        # HOME and HERMES_HOME point into the temp dir so the live-home guard can never see a real path.
        self.env = dict(os.environ, HOME=str(self.root), HERMES_HOME=str(self.root / "live"))
        self.env.pop("PYTHONPATH", None)

    def run_seed(self, *extra, home=None):
        return subprocess.run(
            [sys.executable, str(SEED), str(self.tsv), "--home", str(home or self.home), *extra],
            capture_output=True, text=True, env=self.env, check=False,
        )

    def test_counts_and_manual_source(self):
        res = self.run_seed()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("rows=3 inserted=3 replaced_llm=0 kept_manual=0 manual_total=3 llm_total=0", res.stdout)
        labels, _ = lb_labels.read_all(self.home)
        self.assertEqual({v["source"] for v in labels.values()}, {"manual"})
        self.assertEqual(labels["s2"], {"topic": "BUILD", "value": 3, "summary": "Shipped the crew MR", "source": "manual"})

    def test_topics_come_from_the_data_file_of_that_home(self):
        (self.home / "logbuch").mkdir(parents=True)
        support.write_data(self.home / "logbuch" / "data.json")
        self.tsv.write_text("s1\tSYNC\t2\tNightly job\n", encoding="utf-8")
        res = self.run_seed()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.tsv.write_text("s2\tBUILD\t2\tNot in that file\n", encoding="utf-8")
        res = self.run_seed()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("unknown topic", res.stderr)

    def test_idempotent_and_keeps_later_edits(self):
        self.run_seed()
        lb_labels.put_manual(self.home, "s1", {"topic": "GIT", "value": 1, "summary": "edited"}, None)
        res = self.run_seed()
        self.assertIn("inserted=0 replaced_llm=0 kept_manual=3 manual_total=3", res.stdout)
        labels, _ = lb_labels.read_all(self.home)
        self.assertEqual(labels["s1"]["summary"], "edited")

    def test_replaces_an_llm_label(self):
        lb_labels.put_llm(self.home, "s1", "GIT", 0, "model")
        res = self.run_seed()
        self.assertIn("inserted=2 replaced_llm=1", res.stdout)
        labels, _ = lb_labels.read_all(self.home)
        self.assertEqual(labels["s1"]["source"], "manual")

    def test_refuses_the_live_home_without_the_flag_and_writes_nothing(self):
        live = self.root / "live"
        res = self.run_seed(home=live)
        self.assertEqual(res.returncode, 2)
        self.assertIn("refusing the live Hermes home", res.stderr)
        self.assertFalse(live.exists())
        res = self.run_seed(home=self.root / ".hermes")
        self.assertEqual(res.returncode, 2)
        self.assertFalse((self.root / ".hermes").exists())

    def test_the_flag_allows_it(self):
        res = self.run_seed("--allow-live", home=self.root / "live")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_bad_rows_abort_before_any_write(self):
        for bad in ("s1\tNOPE\t1\tx\n", "s1\tOPS\t9\tx\n", "s1\tOPS\tx\ty\n", "s1\tOPS\t1\n", "s1\tOPS\t1\tx\ns1\tOPS\t2\ty\n"):
            with self.subTest(bad=bad):
                self.tsv.write_text(bad, encoding="utf-8")
                res = self.run_seed()
                self.assertNotEqual(res.returncode, 0)
                self.assertFalse(self.home.exists())

    def test_summary_is_cut_to_120(self):
        self.tsv.write_text("s1\tOPS\t1\t" + "y" * 200 + "\n", encoding="utf-8")
        self.run_seed()
        labels, _ = lb_labels.read_all(self.home)
        self.assertEqual(len(labels["s1"]["summary"]), 120)


if __name__ == "__main__":
    unittest.main()
