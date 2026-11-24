"""Rules layer: which signals fire, label versus hint, precedence, summary."""

from __future__ import annotations

import sys
import unittest

import support

sys.path.insert(0, str(support.DASHBOARD))
import lb_rules  # noqa: E402

TOPICS = support.DATA.topics
NOTHING = {"label": None, "hint": None, "rule": None}


def ev(**kw) -> dict:
    return lb_rules.evaluate(dict({"title": "Some title", "mr_calls": 0}, **kw), support.DATA.rules)


class TestRules(unittest.TestCase):
    def test_every_rule_names_a_real_topic(self):
        self.assertTrue(support.DATA.rules)
        for rule in support.DATA.rules:
            self.assertIn(rule.topic, TOPICS, rule.name)

    def test_path_rule_emits_label_with_title_as_summary(self):
        res = ev(cwd="/home/u/src/billing/sub", title="Invoice export")
        self.assertEqual(res["label"], {"topic": "BILL", "value": 3, "summary": "Invoice export", "source": "rule"})
        self.assertEqual(res["rule"], "path:billing")

    def test_git_repo_root_counts_like_cwd(self):
        self.assertEqual(ev(git_repo_root="/home/u/src/shop")["label"]["topic"], "SHOP")

    def test_lookalike_paths_do_not_fire(self):
        for path in ("/home/u/src/billing-old", "/home/u/src/not-sync", "/home/u/src/launches", "/srv/src/launch2"):
            with self.subTest(path=path):
                res = ev(cwd=path)
                self.assertIsNone(res["label"])
                self.assertIsNone(res["hint"])

    def test_launch_value_follows_mr_calls(self):
        self.assertEqual(ev(cwd="/home/u/src/launch", mr_calls=4)["label"]["value"], 2)
        self.assertEqual(ev(cwd="/home/u/src/launch", mr_calls=5)["label"]["value"], 3)
        self.assertEqual(ev(cwd="/home/u/src/launch-wt/x", mr_calls=0)["label"]["topic"], "LAUNCH")

    def test_topic_only_rule_is_a_hint_without_a_label(self):
        res = ev(cwd="/home/u/src/sync")
        self.assertIsNone(res["label"])
        self.assertEqual(res["hint"], "SYNC")

    def test_host_names_in_title_or_first_prompt(self):
        res = ev(first_prompt="check edge-cache-02 disk")
        self.assertEqual((res["label"], res["hint"]), (None, "EDGE"))
        self.assertEqual(ev(title="shop-db-01 outage")["label"]["topic"], "SHOP")
        self.assertEqual(ev(first_prompt="terraform upgrade")["hint"], "OPS")

    def test_ticket_key_hint(self):
        self.assertEqual(ev(title="BILLING-17 stage B")["hint"], "LAUNCH")
        self.assertIsNone(ev(title="ORDERING-455 something")["hint"])  # a key with no rule maps to nothing

    def test_host_in_a_long_prompt_tail_is_ignored(self):
        self.assertIsNone(ev(first_prompt="x" * 700 + " edge-cache-02")["hint"])

    def test_a_valued_rule_beats_an_earlier_hint(self):
        res = ev(cwd="/home/u/src/shop", title="BILLING-9 edge-cache-01")
        self.assertEqual(res["label"]["topic"], "SHOP")

    def test_first_hint_wins_when_nothing_has_a_value(self):
        self.assertEqual(ev(cwd="/home/u/src/sync", title="ops-vault-01")["hint"], "SYNC")

    def test_summary_is_cut_and_untitled_survives(self):
        self.assertEqual(len(ev(cwd="/src/shop", title="t" * 200)["label"]["summary"]), 120)
        self.assertEqual(lb_rules.evaluate({"cwd": "/src/shop"}, support.DATA.rules)["label"]["summary"], "(untitled)")

    def test_no_signal_no_result(self):
        self.assertEqual(ev(), NOTHING)

    def test_no_rules_no_result(self):
        self.assertEqual(lb_rules.evaluate({"cwd": "/src/shop", "title": "BILLING-1"}, ()), NOTHING)


if __name__ == "__main__":
    unittest.main()
