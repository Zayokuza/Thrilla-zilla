import io
import os
import unittest
from unittest.mock import patch

from thrilla.colors import ColorMode, Palette, strip_ansi


class TTY(io.StringIO):
    def isatty(self):
        return True


class ColorTests(unittest.TestCase):
    def test_forced_color_and_strip(self):
        palette = Palette(ColorMode.ALWAYS, TTY())
        painted = palette.answer("Thrilla")
        self.assertIn("\033[", painted)
        self.assertEqual("Thrilla", strip_ansi(painted))
        self.assertTrue(palette.start("prompt").startswith("\033["))
        self.assertEqual("\033[0m", palette.reset_code)

    def test_never_is_plain(self):
        palette = Palette(ColorMode.NEVER, TTY())
        self.assertEqual("you>", palette.prompt("you>"))

    def test_no_color_environment_disables_auto(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            palette = Palette(ColorMode.AUTO, TTY())
        self.assertFalse(palette.enabled)


if __name__ == "__main__":
    unittest.main()
