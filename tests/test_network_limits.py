"""Stage 5 RED tests for network limit defaults and persistence."""

import tempfile
import unittest
from pathlib import Path

from thrilla.config import Config
from thrilla.limits import DEFAULT_LIMITS, LimitMode


REQUIRED_NETWORK_LIMITS = {
    "network.public_read": True,
    "network.write_actions": False,
    "network.fetch_timeout": 15.0,
    "network.fetch_bytes": 2_000_000,
    "network.redirects": 5,
    "network.research_workers": 3,
    "network.cache_entries": 256,
    "network.cache_age_seconds": 3600,
}


class NetworkLimitDefaultsTests(unittest.TestCase):
    def test_required_stage5_network_limits_are_registered(self):
        names = set(DEFAULT_LIMITS.names())

        for name in REQUIRED_NETWORK_LIMITS:
            with self.subTest(name=name):
                self.assertIn(name, names)

    def test_required_stage5_network_limits_have_locked_defaults(self):
        for name, expected in REQUIRED_NETWORK_LIMITS.items():
            with self.subTest(name=name):
                spec = DEFAULT_LIMITS.get(name)
                self.assertIs(spec.default_mode, LimitMode.AUTO)
                self.assertEqual(spec.default_value, expected)

    def test_config_resolves_stage5_network_auto_defaults(self):
        config = Config.defaults()

        for name, expected in REQUIRED_NETWORK_LIMITS.items():
            with self.subTest(name=name):
                decision = config.resolve_limit(name)
                self.assertIs(decision.mode, LimitMode.AUTO)
                self.assertEqual(decision.value, expected)

    def test_existing_remote_model_limit_is_preserved(self):
        names = set(DEFAULT_LIMITS.names())
        self.assertIn("network.remote_model", names)
        self.assertFalse(
            DEFAULT_LIMITS.get("network.remote_model").default_value
        )

    def test_configured_stage5_network_limit_overrides_default(self):
        config = Config.defaults()
        config.limit_modes["network.fetch_timeout"] = "on"
        config.limit_values["network.fetch_timeout"] = 22.5

        decision = config.resolve_limit("network.fetch_timeout")

        self.assertIs(decision.mode, LimitMode.ON)
        self.assertEqual(decision.value, 22.5)
        self.assertEqual(decision.source, "configured")

    def test_off_mode_removes_thrilla_software_limit(self):
        config = Config.defaults()
        config.limit_modes["network.fetch_bytes"] = "off"

        decision = config.resolve_limit("network.fetch_bytes")

        self.assertIs(decision.mode, LimitMode.OFF)
        self.assertIsNone(decision.value)

    def test_stage5_network_overrides_persist_through_config_save_load(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "config.json"
            config = Config.defaults()
            config.limit_modes["network.research_workers"] = "on"
            config.limit_values["network.research_workers"] = 2
            config.save(path)

            loaded = Config.load(path)
            decision = loaded.resolve_limit("network.research_workers")

            self.assertIs(decision.mode, LimitMode.ON)
            self.assertEqual(decision.value, 2)


if __name__ == "__main__":
    unittest.main()

