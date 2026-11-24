"""private/logbuch/data.json says what the constants on main said (skipped where private/ is absent)."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest

import support

PRIVATE = support.PLUGIN.parents[1] / "private" / "logbuch"
DATA_FILE = PRIVATE / "data.json"
CONSTANTS = PRIVATE / "main_constants.py"


@unittest.skipUnless(DATA_FILE.is_file() and CONSTANTS.is_file(), "private/logbuch is not part of this checkout")
class TestPrivateDataEqualsMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("main_constants", CONSTANTS)
        cls.main = importlib.util.module_from_spec(spec)
        sys.modules["main_constants"] = cls.main
        spec.loader.exec_module(cls.main)
        cls.data = support.lb_data.parse(json.loads(DATA_FILE.read_text(encoding="utf-8")), ("private",))

    def test_topics_and_their_order(self):
        self.assertEqual(self.data.topics, self.main.TOPICS)
        self.assertEqual(list(self.data.topics), list(self.main.TOPICS))

    def test_loose_end(self):
        self.assertEqual((self.data.loose.pattern, self.data.loose.flags), (self.main.LOOSE.pattern, self.main.LOOSE.flags))

    def test_open_states_and_their_order(self):
        got = [(s, p.pattern, p.flags) for s, p in self.data.open_patterns]
        want = [(s, p.pattern, p.flags) for s, p in self.main.OPEN_PATTERNS]
        self.assertEqual(got, want)

    def test_rubric(self):
        self.assertEqual("Value rubric: " + self.data.rubric + "\n", self.main.RUBRIC_LINE)

    def test_rules_in_order(self):
        self.assertEqual(len(self.data.rules), len(self.main.RULES))
        for new, old in zip(self.data.rules, self.main.RULES):
            with self.subTest(old.name):
                self.assertEqual(
                    (new.name, new.field, new.pattern.pattern, new.pattern.flags, new.topic),
                    (old.name, old.field, old.pattern.pattern, old.pattern.flags, old.topic),
                )
                self.assertEqual(callable(new.value), callable(old.value))
                for mr_calls in range(10):
                    item = {"mr_calls": mr_calls}
                    got = new.value(item) if callable(new.value) else new.value
                    want = old.value(item) if callable(old.value) else old.value
                    self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
