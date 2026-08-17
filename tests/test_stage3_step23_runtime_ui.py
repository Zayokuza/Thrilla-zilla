"""Stage 3 Step 23 Runtime & Models UI RED tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import thrilla.app as app_module


class RuntimeModelsMenuTests(unittest.TestCase):
    def test_main_menu_item_four_is_runtime_and_models(self):
        item = next(item for item in app_module.MAIN_MENU if item.key == "4")
        self.assertEqual(item.label, "Runtime & Models")

    def test_runtime_menu_has_expected_entries(self):
        self.assertTrue(hasattr(app_module, "RUNTIME_MENU"))
        items = [(item.key, item.label) for item in app_module.RUNTIME_MENU]
        self.assertEqual(
            items,
            [
                ("1", "Runtime Status"),
                ("2", "Model Inventory"),
                ("3", "Preferred Model"),
                ("4", "Refresh"),
                ("0", "Back"),
            ],
        )

    def test_main_handler_four_opens_runtime_models(self):
        app = object.__new__(app_module.ThrillaApp)
        handlers = app.main_handlers()
        self.assertEqual(handlers["4"].__name__, "runtime_models")

    def test_runtime_handler_map_is_complete(self):
        app = object.__new__(app_module.ThrillaApp)
        self.assertTrue(hasattr(app, "runtime_handlers"))
        handlers = app.runtime_handlers()
        self.assertEqual(set(handlers), {"1", "2", "3", "4"})
        self.assertEqual(handlers["1"].__name__, "runtime_status_screen")
        self.assertEqual(handlers["2"].__name__, "model_inventory_screen")
        self.assertEqual(handlers["3"].__name__, "preferred_model_screen")
        self.assertEqual(handlers["4"].__name__, "refresh_runtime_models")


class RuntimeStatusScreenTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(app_module.ThrillaApp)
        app.config = SimpleNamespace(
            model_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="local-model",
        )
        snapshot = SimpleNamespace(
            configured_endpoint=app.config.model_url,
            expected_model=app.config.model_name,
            ready=True,
            detail="compatible OpenAI endpoint",
            host="127.0.0.1",
            port=8080,
            ownership=None,
            reported_models=("local-model",),
            error="",
        )
        app.runtime_manager = Mock()
        app.runtime_manager.inspect_configured_runtime.return_value = snapshot
        app.model = Mock()
        app._header = Mock()
        app._status = Mock()
        app._pause = Mock()
        return app

    def test_runtime_status_uses_runtime_manager_once(self):
        app = self.make_app()
        self.assertTrue(hasattr(app, "runtime_status_screen"))
        app.runtime_status_screen()
        app.runtime_manager.inspect_configured_runtime.assert_called_once_with(
            app.config.model_url,
            app.config.model_name,
        )

    def test_runtime_status_navigation_never_calls_model_health_or_chat(self):
        app = self.make_app()
        self.assertTrue(hasattr(app, "runtime_status_screen"))
        app.runtime_status_screen()
        app.model.health.assert_not_called()
        app.model.chat.assert_not_called()


if __name__ == "__main__":
    unittest.main()
