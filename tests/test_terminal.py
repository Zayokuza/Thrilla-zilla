import io
import unittest
from unittest.mock import patch

from thrilla.app import MAIN_MENU
from thrilla.colors import ColorMode, Palette
from thrilla.terminal import MenuItem, parse_choice, select_menu


class TerminalMenuTests(unittest.TestCase):
    def test_every_main_menu_key_is_unique(self):
        keys = [item.key for item in MAIN_MENU]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual([str(value) for value in range(1, 10)] + ["0"], keys)

    def test_option_five_regression(self):
        self.assertEqual("5", parse_choice("5", MAIN_MENU))
        self.assertEqual("5", parse_choice("5 doesnt even work", MAIN_MENU))

    def test_names_and_back_work(self):
        items = (MenuItem("1", "Donor Library"), MenuItem("0", "Back"))
        self.assertEqual("1", parse_choice("donor", items))
        self.assertEqual("0", parse_choice("quit", items))

    def test_line_mode_executes_option_five(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="5 doesnt even work"):
            selected = select_menu("TEST", MAIN_MENU, Palette(ColorMode.NEVER), stream=output)
        self.assertEqual("5", selected)

    def test_ctrl_c_in_line_mode_returns_back(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            selected = select_menu("TEST", MAIN_MENU, Palette(ColorMode.NEVER), stream=output)
        self.assertEqual("0", selected)

    def test_ctrl_c_in_interactive_mode_returns_back(self):
        class TTY(io.StringIO):
            def isatty(self):
                return True

        output = TTY()
        input_stream = TTY()
        with patch("thrilla.terminal.read_key", side_effect=KeyboardInterrupt):
            selected = select_menu(
                "TEST",
                MAIN_MENU,
                Palette(ColorMode.NEVER),
                stream=output,
                input_stream=input_stream,
            )
        self.assertEqual("0", selected)


if __name__ == "__main__":
    unittest.main()
