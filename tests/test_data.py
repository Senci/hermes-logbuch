"""The data file: lookup order, validation, fallback to the default, caching, the shipped example."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support

lb_data = support.lb_data
EXAMPLE = support.PLUGIN / "examples" / "data.example.json"


def raw(**changes) -> dict:
    out = json.loads(json.dumps(support.TEST_RAW))
    out.update(changes)
    return out


class DataCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        self.other = Path(self._tmp.name) / "other.json"

    def home_file(self) -> Path:
        path = self.home / "logbuch" / "data.json"
        path.parent.mkdir(exist_ok=True)
        return path


class TestLookup(DataCase):
    def test_no_file_and_no_setting_is_the_neutral_default(self):
        data = lb_data.load(self.home)
        self.assertIs(data, lb_data.DEFAULT)
        self.assertEqual(len(data.topics), 6)
        self.assertEqual(data.rules, ())
        self.assertFalse((self.home / "logbuch").exists())

    def test_the_default_has_generic_phrases_and_no_paths_or_hosts(self):
        blob = json.dumps(lb_data.DEFAULT_RAW)
        self.assertIn("need(s)? your go", blob)
        self.assertNotIn("/", blob)
        self.assertEqual(list(lb_data.DEFAULT.topics), ["BUILD", "OPS", "DOCS", "REVIEW", "TOOLS", "PERSONAL"])
        for state, pattern in lb_data.DEFAULT.open_patterns:
            self.assertIn(state, lb_data.OPEN_STATES)
            self.assertTrue(pattern.pattern)

    def test_the_file_in_the_home_is_used(self):
        support.write_data(self.home_file())
        data = lb_data.load(self.home)
        self.assertEqual(data.topics, support.TEST_RAW["topics"])
        self.assertEqual(len(data.rules), len(support.TEST_RAW["rules"]))

    def test_the_setting_beats_the_home_file(self):
        support.write_data(self.home_file())
        support.write_data(self.other, raw(topics={"ONE": "Only one"}, rules=[]))
        support.use_settings(self, data_file=str(self.other))
        self.assertEqual(lb_data.load(self.home).topics, {"ONE": "Only one"})

    def test_a_missing_configured_file_logs_once_and_falls_back(self):
        support.use_settings(self, data_file=str(self.other))
        with self.assertLogs("logbuch.data", "ERROR") as logs:
            self.assertIs(lb_data.load(self.home), lb_data.DEFAULT)
            self.assertIs(lb_data.load(self.home), lb_data.DEFAULT)
        self.assertEqual(len(logs.records), 1)

    def test_missing_sections_take_the_default(self):
        support.write_data(self.home_file(), {"topics": {"ONE": "Only one"}})
        data = lb_data.load(self.home)
        self.assertEqual(data.topics, {"ONE": "Only one"})
        self.assertEqual(data.rules, ())
        self.assertEqual(data.rubric, lb_data.DEFAULT.rubric)
        self.assertEqual(data.loose.pattern, lb_data.DEFAULT.loose.pattern)
        self.assertEqual([s for s, _p in data.open_patterns], list(lb_data.OPEN_STATES))

    def test_a_changed_file_is_reloaded_and_the_key_moves(self):
        path = support.write_data(self.home_file())
        first = lb_data.load(self.home)
        self.assertIs(lb_data.load(self.home), first)
        support.write_data(path, raw(topics={"ONE": "Only one"}, rules=[]))
        second = lb_data.load(self.home)
        self.assertEqual(second.topics, {"ONE": "Only one"})
        self.assertNotEqual(first.key, second.key)


class TestBadFile(DataCase):
    def test_garbage_logs_one_error_and_the_default_stands_in(self):
        path = self.home_file()
        path.write_text("{ not json", encoding="utf-8")
        with self.assertLogs("logbuch.data", "ERROR") as logs:
            for _ in range(3):
                self.assertIs(lb_data.load(self.home), lb_data.DEFAULT)
        self.assertEqual(len(logs.records), 1)
        self.assertIn(str(path), logs.output[0])

    def test_a_fixed_file_takes_over_again(self):
        path = self.home_file()
        path.write_text("[]", encoding="utf-8")
        with self.assertLogs("logbuch.data", "ERROR"):
            self.assertIs(lb_data.load(self.home), lb_data.DEFAULT)
        support.write_data(path)
        self.assertEqual(lb_data.load(self.home).topics, support.TEST_RAW["topics"])

    def test_every_kind_of_invalid_content_is_refused(self):
        rule = support.TEST_RAW["rules"][1]
        cases = {
            "not an object": [],
            "unknown key": raw(extra=1),
            "no topics": {k: v for k, v in support.TEST_RAW.items() if k != "topics"},
            "empty topics": raw(topics={}),
            "topics not an object": raw(topics=["A"]),
            "blank topic name": raw(topics={"A": " "}),
            "topic name not a string": raw(topics={"A": 5}),
            "bad loose_end regex": raw(loose_end="("),
            "loose_end not a string": raw(loose_end=3),
            "unknown open state": raw(open_states={"maybe": "x"}),
            "bad open state regex": raw(open_states={"todo": "["}),
            "open_states a list": raw(open_states=["todo"]),
            "empty rubric": raw(rubric=" "),
            "rules not a list": raw(rules={}),
            "rule not an object": raw(rules=["x"]),
            "rule missing pattern": raw(rules=[{k: v for k, v in rule.items() if k != "pattern"}]),
            "rule unknown key": raw(rules=[dict(rule, extra=1)]),
            "rule bad field": raw(rules=[dict(rule, field="title")]),
            "rule unknown topic": raw(rules=[dict(rule, topic="NOPE")]),
            "rule bad regex": raw(rules=[dict(rule, pattern="(")]),
            "rule blank name": raw(rules=[dict(rule, name="")]),
            "rule value 4": raw(rules=[dict(rule, value=4)]),
            "rule value bool": raw(rules=[dict(rule, value=True)]),
            "rule value string": raw(rules=[dict(rule, value="3")]),
            "branch missing key": raw(rules=[dict(rule, value={"mr_calls_at_least": 5, "value": 3})]),
            "branch zero threshold": raw(rules=[dict(rule, value={"mr_calls_at_least": 0, "value": 3, "otherwise": 2})]),
            "branch bad value": raw(rules=[dict(rule, value={"mr_calls_at_least": 5, "value": 9, "otherwise": 2})]),
            "duplicate rule names": raw(rules=[rule, rule]),
        }
        for name, content in cases.items():
            with self.subTest(name), self.assertRaises(lb_data.DataError):
                lb_data.parse(content, ("t",))

    def test_a_null_value_is_a_hint_only_rule(self):
        data = lb_data.parse(raw(rules=[dict(support.TEST_RAW["rules"][3], value=None)]), ("t",))
        self.assertIsNone(data.rules[0].value)


class TestExample(unittest.TestCase):
    def test_the_shipped_example_is_valid_and_neutral(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        data = lb_data.parse(json.loads(text), ("example",))
        self.assertGreaterEqual(len(data.topics), 3)
        self.assertTrue(data.rules)
        self.assertEqual(sorted(json.loads(text)), sorted(lb_data.FILE_KEYS))
        for shape in ("/home/", "@", "https://"):
            self.assertNotIn(shape, text)

    def test_the_example_rules_fire(self):
        import lb_rules

        data = lb_data.parse(json.loads(EXAMPLE.read_text(encoding="utf-8")), ("example",))
        hit = lb_rules.evaluate({"cwd": "/home/u/src/billing", "title": "t"}, data.rules)
        self.assertEqual((hit["label"]["topic"], hit["label"]["value"]), ("BILL", 3))
        launch = {"cwd": "/home/u/src/storefront", "title": "t"}
        self.assertEqual(lb_rules.evaluate(dict(launch, mr_calls=4), data.rules)["label"]["value"], 2)
        self.assertEqual(lb_rules.evaluate(dict(launch, mr_calls=5), data.rules)["label"]["value"], 3)


if __name__ == "__main__":
    unittest.main()
