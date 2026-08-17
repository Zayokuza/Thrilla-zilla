"""Stage 3 Step 25 Runtime Policies RED tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import thrilla.app as app_module
from thrilla.config import Config
from thrilla.limits import DEFAULT_LIMITS


class RuntimePolicyMenuTests(unittest.TestCase):
    def test_settings_menu_exposes_runtime_policies(self):
        matches = [
            item for item in app_module.SETTINGS_MENU
            if item.label == "Runtime Policies"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].key, "7")

    def test_settings_handler_routes_runtime_policies(self):
        app = object.__new__(app_module.ThrillaApp)
        handlers = app.settings_handlers()
        self.assertIn("7", handlers)
        self.assertEqual(
            handlers["7"].__name__,
            "runtime_policies_screen",
        )


class RuntimePolicyDisplayTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(app_module.ThrillaApp)
        app.config = Config.defaults()
        app.config.limit_default_mode = "auto"
        app.config.limit_modes = {
            "runtime.cpu_threads": "off",
        }
        app.config.limit_values = {
            "runtime.cpu_threads": 3,
        }
        app._header = Mock()
        app._status = Mock()
        app._pause = Mock()
        app._prompt = Mock(return_value="")
        app.audit = Mock()
        return app

    def rendered(self, app):
        return " ".join(
            str(arg)
            for call in app._status.call_args_list
            for arg in call.args
        )

    def test_global_default_mode_is_displayed(self):
        app = self.make_app()
        self.assertTrue(
            hasattr(app, "runtime_policies_screen")
        )
        app.runtime_policies_screen()
        rendered = self.rendered(app)
        self.assertIn("Global default", rendered)
        self.assertIn("AUTO", rendered)

    def test_per_limit_override_and_value_are_displayed(self):
        app = self.make_app()
        self.assertTrue(
            hasattr(app, "runtime_policies_screen")
        )
        app.runtime_policies_screen()
        rendered = self.rendered(app)
        self.assertIn("runtime.cpu_threads", rendered)
        self.assertIn("OFF", rendered)
        self.assertIn("3", rendered)

    def test_registered_limits_are_displayed(self):
        app = self.make_app()
        self.assertTrue(
            hasattr(app, "runtime_policies_screen")
        )
        app.runtime_policies_screen()
        rendered = self.rendered(app)
        for name in DEFAULT_LIMITS.names():
            with self.subTest(name=name):
                self.assertIn(name, rendered)


class RuntimePolicyPersistenceTests(unittest.TestCase):
    def make_app(self, root):
        app = object.__new__(app_module.ThrillaApp)
        app.config = Config.defaults()
        app.config.state_root = str(root)
        app.audit = Mock()
        return app

    def assert_mode_persists(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = self.make_app(root)
            app.set_runtime_policy_mode(
                "runtime.cpu_threads",
                mode,
            )
            loaded = Config.load(root / "config.json")
            self.assertEqual(
                loaded.limit_modes["runtime.cpu_threads"],
                mode,
            )

    def test_on_persists(self):
        self.assert_mode_persists("on")

    def test_auto_persists(self):
        self.assert_mode_persists("auto")

    def test_off_persists(self):
        self.assert_mode_persists("off")

    def test_policy_change_audits_name_and_mode_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.make_app(Path(tmp))
            app.set_runtime_policy_mode(
                "runtime.cpu_threads",
                "on",
            )
            app.audit.write.assert_called_once()
            call = app.audit.write.call_args
            self.assertEqual(
                call.args[0],
                "runtime_policy_changed",
            )
            self.assertEqual(
                call.kwargs["limit_name"],
                "runtime.cpu_threads",
            )
            self.assertEqual(call.kwargs["mode"], "on")
            self.assertNotIn("prompt", call.kwargs)


if __name__ == "__main__":
    unittest.main()
