import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from thrilla import app as app_module
from thrilla.app import ThrillaApp
from thrilla.config import Config


class CreatorVaultUITests(unittest.TestCase):
    def make_app(self, unlocked=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        config.owner_name = "Jesse James"
        config.creator_vault_unlocked = unlocked

        app = ThrillaApp(config)
        app._header = Mock()
        app._pause = Mock()
        app._status = Mock()

        return app, config

    def test_settings_menu_exposes_creator_vault(self):
        labels = {
            item.key: item.label
            for item in app_module.SETTINGS_MENU
        }

        self.assertEqual(labels.get("8"), "Creator Vault")

    def test_settings_handler_routes_creator_vault(self):
        app, _ = self.make_app()

        handler = app.settings_handlers().get("8")

        self.assertIsNotNone(handler)
        self.assertEqual(
            handler.__func__,
            app.creator_vault_screen.__func__,
        )

    def test_locked_vault_shows_locked_screen(self):
        app, config = self.make_app(False)
        app._input_line = Mock(return_value="wrong")

        app.creator_vault_screen()

        app._header.assert_any_call("CREATOR VAULT: LOCKED")
        self.assertFalse(config.creator_vault_unlocked)

    def test_wrong_code_does_not_unlock(self):
        app, config = self.make_app(False)
        app._input_line = Mock(return_value="nope")
        config.save = Mock()
        app.audit.write = Mock()

        app.creator_vault_screen()

        self.assertFalse(config.creator_vault_unlocked)
        config.save.assert_not_called()
        app.audit.write.assert_not_called()

    def test_exact_code_unlocks_and_persists(self):
        app, config = self.make_app(False)
        app._input_line = Mock(return_value="1989")
        config.save = Mock()
        app.audit.write = Mock()

        with patch(
            "thrilla.app.select_menu",
            return_value="0",
        ):
            app.creator_vault_screen()

        self.assertTrue(config.creator_vault_unlocked)
        config.save.assert_called_once_with()
        app.audit.write.assert_called_once_with(
            "creator_vault_unlocked"
        )
        app._header.assert_any_call("CREATOR VAULT: UNLOCKED")

    def test_unlock_audit_never_contains_entered_code(self):
        app, config = self.make_app(False)
        app._input_line = Mock(return_value="1989")
        config.save = Mock()
        app.audit.write = Mock()

        with patch(
            "thrilla.app.select_menu",
            return_value="0",
        ):
            app.creator_vault_screen()

        audit_text = repr(app.audit.write.call_args_list)

        self.assertNotIn("1989", audit_text)

    def test_already_unlocked_never_requests_code_again(self):
        app, _ = self.make_app(True)
        app._input_line = Mock(
            side_effect=AssertionError("asked for code again")
        )

        with patch(
            "thrilla.app.select_menu",
            return_value="0",
        ):
            app.creator_vault_screen()

        app._input_line.assert_not_called()
        app._header.assert_any_call("CREATOR VAULT: UNLOCKED")


class EquipmentToggleTests(unittest.TestCase):
    def make_app(self, unlocked=True):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        config.owner_name = "Jesse James"
        config.creator_vault_unlocked = unlocked

        app = ThrillaApp(config)
        config.save = Mock()
        app.audit.write = Mock()

        return app, config

    def assert_independent_toggle(self, equipment):
        app, config = self.make_app(True)

        before = dict(config.equipment_states)

        result = app.toggle_equipment(equipment)

        self.assertTrue(result)
        self.assertTrue(config.equipment_states[equipment])

        for name, old_state in before.items():
            if name != equipment:
                self.assertEqual(
                    config.equipment_states[name],
                    old_state,
                )

        self.assertTrue(config.creator_vault_unlocked)

    def test_locked_vault_cannot_toggle_equipment(self):
        app, config = self.make_app(False)

        result = app.toggle_equipment("sword")

        self.assertFalse(result)
        self.assertFalse(config.equipment_states["sword"])
        config.save.assert_not_called()
        app.audit.write.assert_not_called()

    def test_sword_toggles_independently(self):
        self.assert_independent_toggle("sword")

    def test_shield_toggles_independently(self):
        self.assert_independent_toggle("shield")

    def test_helmet_toggles_independently(self):
        self.assert_independent_toggle("helmet")

    def test_armor_toggles_independently(self):
        self.assert_independent_toggle("armor")

    def test_boots_toggle_independently(self):
        self.assert_independent_toggle("boots")

    def test_turning_equipment_off_never_relocks_vault(self):
        app, config = self.make_app(True)

        app.toggle_equipment("sword")
        self.assertTrue(config.equipment_states["sword"])

        result = app.toggle_equipment("sword")

        self.assertFalse(result)
        self.assertFalse(config.equipment_states["sword"])
        self.assertTrue(config.creator_vault_unlocked)

    def test_toggle_audit_contains_name_and_state_only(self):
        app, _ = self.make_app(True)

        app.toggle_equipment("sword")

        app.audit.write.assert_called_once_with(
            "equipment_toggle_changed",
            equipment="sword",
            state=True,
        )

        self.assertNotIn(
            "1989",
            repr(app.audit.write.call_args_list),
        )

    def test_equipment_menu_displays_all_five_states(self):
        app, config = self.make_app(True)

        config.equipment_states["sword"] = True
        config.equipment_states["helmet"] = True

        labels = [
            item.label
            for item in app.creator_vault_menu_items()
        ]

        self.assertIn("Sword - ON", labels)
        self.assertIn("Shield - OFF", labels)
        self.assertIn("Helmet - ON", labels)
        self.assertIn("Armor - OFF", labels)
        self.assertIn("Boots - OFF", labels)

    def test_unlocked_vault_menu_can_toggle_selected_module(self):
        app, config = self.make_app(True)
        app._input_line = Mock(
            side_effect=AssertionError(
                "unlocked vault asked for code"
            )
        )

        with patch(
            "thrilla.app.select_menu",
            side_effect=["1", "0"],
        ):
            app.creator_vault_screen()

        self.assertTrue(config.equipment_states["sword"])
        self.assertFalse(config.equipment_states["shield"])
        self.assertTrue(config.creator_vault_unlocked)


if __name__ == "__main__":
    unittest.main()
