"""Settings: defaults, per-profile overrides, type fallback, Hermes being absent, plugin.yaml in step."""

from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

import support

settings = support.lb_settings


def read_schema_block() -> dict[str, dict[str, str]]:
    """The config_schema of plugin.yaml as {key: {field: text}}; the file is flat enough to read by line."""
    out: dict[str, dict[str, str]] = {}
    inside = False
    key = ""
    for line in (support.PLUGIN / "plugin.yaml").read_text(encoding="utf-8").splitlines():
        if not line.startswith(" "):
            inside = line.rstrip() == "config_schema:"
            continue
        if not inside:
            continue
        name, _, value = line.strip().partition(":")
        if not line.startswith("    "):
            key = name
            out[key] = {}
        else:
            out[key][name] = value.strip().strip('"')
    return out


class TestLoad(unittest.TestCase):
    def load(self, raw):
        with mock.patch.object(settings, "read_entry", return_value=raw):
            return settings.load()

    def test_empty_config_gives_the_defaults(self):
        self.assertEqual(self.load({}), settings.defaults())
        self.assertEqual(settings.defaults(), {
            "data_file": "", "classify_model": "claude-haiku-5-5", "provider": "anthropic", "profile": "default",
            "classify_limit": 20,
        })

    def test_overrides_apply(self):
        got = self.load({"data_file": " /x/data.json ", "classify_model": "m", "provider": "p", "profile": "work", "classify_limit": 5})
        self.assertEqual(got, {"data_file": "/x/data.json", "classify_model": "m", "provider": "p", "profile": "work", "classify_limit": 5})

    def test_wrong_types_fall_back_to_the_default(self):
        got = self.load({"data_file": 5, "classify_model": ["m"], "provider": None, "profile": 1.5, "classify_limit": "20"})
        self.assertEqual(got, settings.defaults())

    def test_non_positive_and_bool_limits_fall_back(self):
        for bad in (0, -4, True, 2.5):
            with self.subTest(bad=bad):
                self.assertEqual(self.load({"classify_limit": bad})["classify_limit"], 20)

    def test_blank_strings_fall_back(self):
        self.assertEqual(self.load({"classify_model": "   ", "profile": ""}), settings.defaults())

    def test_unknown_keys_are_ignored(self):
        self.assertNotIn("bogus", self.load({"bogus": 1}))

    def test_plugin_yaml_declares_exactly_the_schema(self):
        declared = read_schema_block()
        self.assertEqual(sorted(declared), sorted(settings.SCHEMA))
        for key, (kind, default) in settings.SCHEMA.items():
            self.assertEqual(declared[key]["type"], kind, key)
            self.assertEqual(declared[key]["default"], str(default), key)
            self.assertTrue(declared[key]["description"], key)

    def test_no_schema_key_uses_a_hermes_reserved_root(self):
        # hermes_cli/plugins_state.py:17: the settings form drops such a key and saving it raises.
        reserved = {"model", "plugins", "security", "settings"}
        for key in read_schema_block():
            self.assertNotIn(key.split(".")[0].lower(), reserved, key)


class TestReadEntry(unittest.TestCase):
    def fake_hermes(self, config, name="load_config_readonly"):
        module = types.ModuleType("hermes_cli.config")
        setattr(module, name, lambda: config)
        package = types.ModuleType("hermes_cli")
        package.config = module
        return mock.patch.dict(sys.modules, {"hermes_cli": package, "hermes_cli.config": module})

    def read(self):
        return support.REAL_READ_ENTRY()

    def test_hermes_absent_is_empty(self):
        with mock.patch.dict(sys.modules, {"hermes_cli": None, "hermes_cli.config": None}):
            self.assertEqual(self.read(), {})

    def test_reads_plugins_entries_logbuch_settings(self):
        config = {"plugins": {"entries": {"logbuch": {"settings": {"classify_model": "m"}}, "other": {"settings": {"x": 1}}}}}
        with self.fake_hermes(config):
            self.assertEqual(self.read(), {"classify_model": "m"})

    def test_a_hermes_without_the_readonly_loader_is_empty(self):
        with self.fake_hermes({"plugins": {"entries": {"logbuch": {"settings": {"classify_model": "m"}}}}}, name="load_config"):
            self.assertEqual(self.read(), {})

    def test_malformed_config_is_empty(self):
        for config in (None, {"plugins": None}, {"plugins": {"entries": []}}, {"plugins": {"entries": {"logbuch": {"settings": "x"}}}}):
            with self.fake_hermes(config):
                self.assertEqual(self.read(), {})

    def test_a_loader_that_raises_is_empty(self):
        module = types.ModuleType("hermes_cli.config")

        def boom():
            raise RuntimeError("config broken")

        module.load_config_readonly = boom
        package = types.ModuleType("hermes_cli")
        package.config = module
        with mock.patch.dict(sys.modules, {"hermes_cli": package, "hermes_cli.config": module}):
            self.assertEqual(self.read(), {})


if __name__ == "__main__":
    unittest.main()
