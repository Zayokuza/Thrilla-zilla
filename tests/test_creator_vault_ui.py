import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

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

        app.creator_vault_screen()

        audit_text = repr(app.audit.write.call_args_list)

        self.assertNotIn("1989", audit_text)

    def test_already_unlocked_never_requests_code_again(self):
        app, _ = self.make_app(True)
        app._input_line = Mock(
            side_effect=AssertionError("asked for code again")
        )

        app.creator_vault_screen()

        app._input_line.assert_not_called()
        app._header.assert_any_call("CREATOR VAULT: UNLOCKED")


if __name__ == "__main__":
    unittest.main()
