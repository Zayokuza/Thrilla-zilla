import tempfile
import unittest
from pathlib import Path

from thrilla.config import Config


EXPECTED_NAMES = (
    "sword",
    "shield",
    "helmet",
    "armor",
    "boots",
)


class CreatorVaultRestorationTests(unittest.TestCase):
    def make_path(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name) / "config.json"

    def test_restart_restores_exact_equipment_pattern(self):
        path = self.make_path()

        config = Config.defaults()
        config.creator_vault_unlocked = True
        config.equipment_states = {
            "sword": True,
            "shield": False,
            "helmet": True,
            "armor": False,
            "boots": True,
        }

        config.save(path)

        restored = Config.load(path)

        self.assertTrue(
            restored.creator_vault_unlocked
        )

        self.assertEqual(
            restored.equipment_states,
            {
                "sword": True,
                "shield": False,
                "helmet": True,
                "armor": False,
                "boots": True,
            },
        )

    def test_all_equipment_off_does_not_relock_vault(self):
        path = self.make_path()

        config = Config.defaults()
        config.creator_vault_unlocked = True
        config.equipment_states = {
            name: True
            for name in EXPECTED_NAMES
        }

        config.save(path)

        restored = Config.load(path)

        for name in EXPECTED_NAMES:
            restored.equipment_states[name] = False

        restored.save(path)

        restarted = Config.load(path)

        self.assertTrue(
            restarted.creator_vault_unlocked
        )

        self.assertEqual(
            restarted.equipment_states,
            {
                name: False
                for name in EXPECTED_NAMES
            },
        )

    def test_restart_does_not_merge_equipment_states(self):
        path = self.make_path()

        expected = {
            "sword": False,
            "shield": True,
            "helmet": False,
            "armor": True,
            "boots": False,
        }

        config = Config.defaults()
        config.creator_vault_unlocked = True
        config.equipment_states = dict(expected)
        config.save(path)

        restarted = Config.load(path)

        self.assertEqual(
            tuple(restarted.equipment_states),
            EXPECTED_NAMES,
        )

        self.assertEqual(
            restarted.equipment_states,
            expected,
        )

    def test_multiple_restarts_preserve_same_state(self):
        path = self.make_path()

        expected = {
            "sword": True,
            "shield": True,
            "helmet": False,
            "armor": True,
            "boots": False,
        }

        config = Config.defaults()
        config.creator_vault_unlocked = True
        config.equipment_states = dict(expected)
        config.save(path)

        for _ in range(5):
            config = Config.load(path)

            self.assertTrue(
                config.creator_vault_unlocked
            )

            self.assertEqual(
                config.equipment_states,
                expected,
            )

            config.save(path)


if __name__ == "__main__":
    unittest.main()
