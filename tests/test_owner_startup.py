import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from thrilla.app import ThrillaApp
from thrilla.config import Config


class OwnerStartupTests(unittest.TestCase):
    def make_app(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        return ThrillaApp(config), config

    def method(self, app):
        method = getattr(app, "ensure_owner_profile", None)
        self.assertTrue(
            callable(method),
            "ThrillaApp.ensure_owner_profile is missing",
        )
        return method

    def test_missing_owner_asks_exact_question_and_trims_name(self):
        app, config = self.make_app()
        app._input_line = Mock(return_value="  Jesse James  ")
        self.method(app)()
        app._input_line.assert_called_once_with("What is your name?")
        self.assertEqual(config.owner_name, "Jesse James")

    def test_empty_owner_input_repeats_question(self):
        app, config = self.make_app()
        app._input_line = Mock(side_effect=["   ", " Jesse James "])
        self.method(app)()
        self.assertEqual(
            app._input_line.call_args_list,
            [call("What is your name?"), call("What is your name?")],
        )
        self.assertEqual(config.owner_name, "Jesse James")

    def test_stored_owner_skips_enrollment(self):
        app, config = self.make_app()
        config.owner_name = "Jesse James"
        app._input_line = Mock(side_effect=AssertionError("prompted"))
        self.method(app)()
        app._input_line.assert_not_called()

    def test_successful_enrollment_saves_and_audits(self):
        app, config = self.make_app()
        app._input_line = Mock(return_value="Jesse James")
        config.save = Mock()
        app.audit.write = Mock()
        self.method(app)()
        config.save.assert_called_once_with()
        app.audit.write.assert_called_once_with(
            "owner_profile_created"
        )

    def test_run_checks_owner_before_first_menu(self):
        app, config = self.make_app()
        config.owner_name = "Jesse James"
        app.ensure_owner_profile = Mock()
        with patch("thrilla.app.select_menu", return_value="0"):
            app.run()
        app.ensure_owner_profile.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
