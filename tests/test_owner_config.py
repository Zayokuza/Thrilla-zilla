"""Persistent Thrilla owner configuration tests."""

import json
import tempfile
import unittest
from pathlib import Path

from thrilla.config import Config


class OwnerConfigTests(unittest.TestCase):
    def test_new_config_defaults_to_empty_owner(self):
        self.assertEqual(Config.defaults().owner_name, "")

    def test_old_config_without_owner_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "model_name": "existing-model",
                "history_turns": 7,
                "limit_default_mode": "off"
            }), encoding="utf-8")
            config = Config.load(path)
            self.assertEqual(config.owner_name, "")
            self.assertEqual(config.model_name, "existing-model")
            self.assertEqual(config.history_turns, 7)
            self.assertEqual(config.limit_default_mode, "off")

    def test_owner_survives_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = Config.defaults()
            config.owner_name = "Jesse James"
            config.save(path)
            loaded = Config.load(path)
            self.assertEqual(loaded.owner_name, "Jesse James")


if __name__ == "__main__":
    unittest.main()
