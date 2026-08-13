import io
import os
import unittest
from unittest.mock import Mock, patch

from thrilla.app import DONOR_MENU, MAIN_MENU, SETTINGS_MENU, ThrillaApp
from thrilla.colors import ColorMode, Palette, strip_ansi
from thrilla.terminal import MenuItem, _render_menu


class StageOneInterfaceTests(unittest.TestCase):
    def test_narrow_menu_lines_fit_terminal_width(self):
        output = io.StringIO()
        items = (
            MenuItem(
                "1",
                "A deliberately long menu label for a phone terminal",
                "Long description that must not spill beyond the visible terminal width.",
            ),
            MenuItem("0", "Back"),
        )

        with patch(
            "thrilla.terminal.shutil.get_terminal_size",
            return_value=os.terminal_size((32, 10)),
        ):
            _render_menu(
                "A deliberately long Thrilla screen title",
                items,
                0,
                Palette(ColorMode.NEVER),
                output,
                "A long footer explaining controls that must wrap on a narrow phone screen.",
            )

        for line in output.getvalue().splitlines():
            self.assertLessEqual(len(strip_ansi(line)), 32, line)

    def test_main_menu_has_exact_handler_coverage(self):
        app = ThrillaApp()
        self.assertEqual(
            {item.key for item in MAIN_MENU if item.key != "0"},
            set(app.main_handlers()),
        )

    def test_donor_menu_has_exact_handler_coverage(self):
        app = ThrillaApp()
        self.assertEqual(
            {item.key for item in DONOR_MENU if item.key != "0"},
            set(app.donor_handlers()),
        )

    def test_settings_menu_has_exact_handler_coverage(self):
        app = ThrillaApp()
        self.assertEqual(
            {item.key for item in SETTINGS_MENU if item.key != "0"},
            set(app.settings_handlers()),
        )


if __name__ == "__main__":
    unittest.main()


class ChatNavigationAliasTests(unittest.TestCase):
    def test_plain_navigation_aliases_leave_chat_without_model_call(self):
        commands = (
            "back",
            "exit",
            "quit",
            "0",
            "go back",
            "start over",
            "main menu",
            "menu",
            "home",
        )

        for command in commands:
            with self.subTest(command=command):
                app = ThrillaApp.__new__(ThrillaApp)
                app.palette = Palette(ColorMode.NEVER)
                app.model = Mock()

                with patch.object(app, "_header"), patch.object(
                    app,
                    "_input_line",
                    return_value=command,
                ):
                    app.ask()

                app.model.chat.assert_not_called()


