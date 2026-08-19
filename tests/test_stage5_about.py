"""Stage 5 About screen must describe the active system."""

import contextlib
import io
import unittest
from types import SimpleNamespace

from thrilla.app import ThrillaApp


class PlainPalette:
    def brand(self, value):
        return str(value)

    def muted(self, value):
        return str(value)

    def accent(self, value):
        return str(value)


class Stage5AboutTests(unittest.TestCase):
    def test_about_no_longer_calls_web_research_future_work(self):
        app = ThrillaApp.__new__(ThrillaApp)
        app.palette = PlainPalette()
        app.config = SimpleNamespace(owner_name="Tester")
        app._header = lambda title: None
        app._status = lambda *args, **kwargs: None
        app._pause = lambda: None

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            app.about()

        text = " ".join(
            output.getvalue().lower().split()
        )
        self.assertIn("web research", text)
        self.assertIn("background", text)
        self.assertIn("stage 6", text)
        self.assertNotIn(
            "web research and broader workflow autonomy remain later stages",
            text,
        )


if __name__ == "__main__":
    unittest.main()
