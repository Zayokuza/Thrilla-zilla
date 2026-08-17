"""Plan A Task 6 streamlined terminal UI RED tests."""

import unittest

import thrilla.app as app_module


class StreamlinedMainMenuTests(unittest.TestCase):
    def test_main_menu_exact_keys_and_labels(self):
        actual = [
            (item.key, item.label)
            for item in app_module.MAIN_MENU
        ]
        expected = [
            ("1", "Ask Thrilla"),
            ("2", "Donor Library"),
            ("3", "Route Inspector"),
            ("4", "Runtime & Models"),
            ("5", "Diagnostics"),
            ("6", "Conversation History"),
            ("7", "Activity Log"),
            ("8", "Settings"),
            ("9", "About"),
            ("0", "Exit"),
        ]
        self.assertEqual(actual, expected)

    def test_every_main_menu_action_has_expected_handler(self):
        app = object.__new__(app_module.ThrillaApp)
        handlers = app.main_handlers()
        expected = {
            "1": "ask",
            "2": "donor_library",
            "3": "route_inspector",
            "4": "runtime_models",
            "5": "diagnostics_screen",
            "6": "history_screen",
            "7": "audit_screen",
            "8": "settings",
            "9": "about",
        }
        self.assertEqual(set(handlers), set(expected))
        for key, name in expected.items():
            with self.subTest(key=key):
                self.assertEqual(
                    handlers[key].__name__,
                    name,
                )

    def test_main_menu_has_no_repeated_descriptions(self):
        self.assertTrue(
            all(
                item.description == ""
                for item in app_module.MAIN_MENU
            )
        )


class StreamlinedNavigationTests(unittest.TestCase):
    def test_ask_remains_direct_main_menu_entry(self):
        app = object.__new__(app_module.ThrillaApp)
        self.assertEqual(
            app.main_handlers()["1"].__name__,
            "ask",
        )

    def test_runtime_models_is_reachable_from_main_menu(self):
        app = object.__new__(app_module.ThrillaApp)
        self.assertEqual(
            app.main_handlers()["4"].__name__,
            "runtime_models",
        )

    def test_runtime_policies_is_reachable_from_settings(self):
        app = object.__new__(app_module.ThrillaApp)
        handlers = app.settings_handlers()
        matches = [
            item for item in app_module.SETTINGS_MENU
            if item.label == "Runtime Policies"
        ]
        self.assertEqual(len(matches), 1)
        key = matches[0].key
        self.assertIn(key, handlers)
        self.assertEqual(
            handlers[key].__name__,
            "runtime_policies_screen",
        )


if __name__ == "__main__":
    unittest.main()
