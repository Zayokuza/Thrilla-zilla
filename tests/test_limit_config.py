import tempfile
import unittest
from pathlib import Path

from thrilla.config import Config


_MISSING = object()


class LimitConfigTests(unittest.TestCase):
    def test_limit_control_defaults_to_auto_with_no_overrides(self):
        config = Config.defaults()

        self.assertEqual(
            "auto",
            getattr(config, "limit_default_mode", _MISSING),
            "Config requires limit_default_mode='auto'.",
        )
        self.assertEqual(
            {},
            getattr(config, "limit_modes", _MISSING),
            "Config requires an empty limit_modes mapping by default.",
        )
        self.assertEqual(
            {},
            getattr(config, "limit_values", _MISSING),
            "Config requires an empty limit_values mapping by default.",
        )

    def test_limit_control_settings_survive_config_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"

            config = Config.defaults()
            config.limit_default_mode = "off"
            config.limit_modes = {
                "runtime.managed_startup": "on",
                "model.request_timeout": "off",
            }
            config.limit_values = {
                "model.request_timeout": 120.0,
                "memory.history_turns": 24,
            }
            config.save(path)

            loaded = Config.load(path)

            self.assertEqual(
                "off",
                getattr(loaded, "limit_default_mode", _MISSING),
                "limit_default_mode must survive save/load.",
            )
            self.assertEqual(
                {
                    "runtime.managed_startup": "on",
                    "model.request_timeout": "off",
                },
                getattr(loaded, "limit_modes", _MISSING),
                "limit_modes must survive save/load.",
            )
            self.assertEqual(
                {
                    "model.request_timeout": 120.0,
                    "memory.history_turns": 24,
                },
                getattr(loaded, "limit_values", _MISSING),
                "limit_values must survive save/load.",
            )

    def test_invalid_limit_modes_are_sanitized_on_load(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                """{
  "limit_default_mode": "maybe",
  "limit_modes": {
    "runtime.managed_startup": "on",
    "runtime.context_size": "auto",
    "model.request_timeout": "off",
    "runtime.queue_depth": "invalid"
  },
  "limit_values": {
    "runtime.context_size": 4096
  }
}
""",
                encoding="utf-8",
            )

            loaded = Config.load(path)

            self.assertEqual("auto", loaded.limit_default_mode)
            self.assertEqual(
                {
                    "runtime.managed_startup": "on",
                    "runtime.context_size": "auto",
                    "model.request_timeout": "off",
                },
                loaded.limit_modes,
            )
            self.assertEqual(
                {"runtime.context_size": 4096},
                loaded.limit_values,
            )

    def test_malformed_limit_containers_become_empty_mappings(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                """{
  "limit_modes": ["on", "off"],
  "limit_values": "not-a-mapping"
}
""",
                encoding="utf-8",
            )

            loaded = Config.load(path)

            self.assertEqual({}, loaded.limit_modes)
            self.assertEqual({}, loaded.limit_values)

    def test_config_resolves_limit_using_global_auto_mode(self):
        config = Config.defaults()

        resolve = getattr(config, "resolve_limit", None)
        if not callable(resolve):
            self.fail("Config requires resolve_limit().")

        decision = resolve(
            "model.request_timeout",
            auto_value=75.0,
        )

        self.assertEqual("auto", decision.mode.value)
        self.assertEqual(75.0, decision.value)
        self.assertEqual("auto", decision.source)

    def test_per_limit_mode_and_value_override_global_mode(self):
        config = Config.defaults()
        config.limit_default_mode = "off"
        config.limit_modes = {
            "model.request_timeout": "on",
        }
        config.limit_values = {
            "model.request_timeout": 120.0,
        }

        resolve = getattr(config, "resolve_limit", None)
        if not callable(resolve):
            self.fail("Config requires resolve_limit().")

        decision = resolve(
            "model.request_timeout",
            auto_value=75.0,
        )

        self.assertEqual("on", decision.mode.value)
        self.assertEqual(120.0, decision.value)
        self.assertEqual("configured", decision.source)

    def test_global_off_applies_when_no_per_limit_override_exists(self):
        config = Config.defaults()
        config.limit_default_mode = "off"

        resolve = getattr(config, "resolve_limit", None)
        if not callable(resolve):
            self.fail("Config requires resolve_limit().")

        decision = resolve(
            "runtime.context_size",
            auto_value=4096,
        )

        self.assertEqual("off", decision.mode.value)
        self.assertIsNone(decision.value)
        self.assertEqual("off", decision.source)

    def test_existing_model_timeout_feeds_limit_resolution(self):
        config = Config.defaults()
        config.request_timeout = 135.0

        auto = config.resolve_limit("model.request_timeout")
        self.assertEqual("auto", auto.mode.value)
        self.assertEqual(135.0, auto.value)

        config.limit_default_mode = "on"
        on = config.resolve_limit("model.request_timeout")
        self.assertEqual("on", on.mode.value)
        self.assertEqual(135.0, on.value)

    def test_existing_history_turns_feed_limit_resolution(self):
        config = Config.defaults()
        config.history_turns = 18

        auto = config.resolve_limit("memory.history_turns")
        self.assertEqual(18, auto.value)

        config.limit_default_mode = "on"
        on = config.resolve_limit("memory.history_turns")
        self.assertEqual(18, on.value)

    def test_existing_donor_timeout_default_feeds_limit_resolution(self):
        config = Config.defaults()

        auto = config.resolve_limit("donor.git_timeout")
        self.assertEqual(4.0, auto.value)

        config.limit_default_mode = "on"
        on = config.resolve_limit("donor.git_timeout")
        self.assertEqual(4.0, on.value)

    def test_remote_model_environment_feeds_auto_resolution(self):
        import os
        from unittest.mock import patch

        config = Config.defaults()

        with patch.dict(
            os.environ,
            {"THRILLA_ALLOW_REMOTE_MODEL": "1"},
            clear=False,
        ):
            allowed = config.resolve_limit("network.remote_model")
            self.assertIs(True, allowed.value)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("THRILLA_ALLOW_REMOTE_MODEL", None)
            blocked = config.resolve_limit("network.remote_model")
            self.assertIs(False, blocked.value)

    def test_explicit_limit_value_beats_legacy_value(self):
        config = Config.defaults()
        config.request_timeout = 135.0
        config.limit_values = {
            "model.request_timeout": 210.0,
        }

        decision = config.resolve_limit("model.request_timeout")

        self.assertEqual(210.0, decision.value)


if __name__ == "__main__":
    unittest.main()
