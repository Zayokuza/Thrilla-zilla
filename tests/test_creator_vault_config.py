import json
import tempfile
import unittest
from pathlib import Path

from thrilla.config import Config


EXPECTED_OFF = {
    "sword": False,
    "shield": False,
    "helmet": False,
    "armor": False,
    "boots": False,
}


class CreatorVaultConfigTests(unittest.TestCase):
    def test_new_installation_is_locked_with_all_equipment_off(self):
        config = Config.defaults()

        self.assertFalse(config.creator_vault_unlocked)
        self.assertEqual(config.equipment_states, EXPECTED_OFF)

    def test_old_config_without_vault_fields_migrates_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps({
                    "owner_name": "Jesse James",
                    "model_name": "existing-model",
                }),
                encoding="utf-8",
            )

            config = Config.load(path)

        self.assertFalse(config.creator_vault_unlocked)
        self.assertEqual(config.equipment_states, EXPECTED_OFF)
        self.assertEqual(config.owner_name, "Jesse James")
        self.assertEqual(config.model_name, "existing-model")

    def test_unlock_survives_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            config = Config.defaults()
            config.creator_vault_unlocked = True
            config.save(path)

            loaded = Config.load(path)

            self.assertTrue(loaded.creator_vault_unlocked)

    def test_mixed_equipment_state_survives_reload_exactly(self):
        mixed = {
            "sword": True,
            "shield": False,
            "helmet": True,
            "armor": False,
            "boots": True,
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            config = Config.defaults()
            config.creator_vault_unlocked = True
            config.equipment_states = dict(mixed)
            config.save(path)

            loaded = Config.load(path)

            self.assertTrue(loaded.creator_vault_unlocked)
            self.assertEqual(loaded.equipment_states, mixed)

    def test_missing_keys_default_off_and_unknown_keys_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            path.write_text(
                json.dumps({
                    "creator_vault_unlocked": True,
                    "equipment_states": {
                        "sword": True,
                        "laser": True,
                    },
                }),
                encoding="utf-8",
            )

            loaded = Config.load(path)

        self.assertEqual(
            loaded.equipment_states,
            {
                "sword": True,
                "shield": False,
                "helmet": False,
                "armor": False,
                "boots": False,
            },
        )
        self.assertNotIn("laser", loaded.equipment_states)


if __name__ == "__main__":
    unittest.main()
