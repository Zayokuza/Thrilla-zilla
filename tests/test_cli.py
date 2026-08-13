import contextlib
import io
import json
import unittest

from thrilla.cli import main


class CLITests(unittest.TestCase):
    def test_route_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["route", "debug", "python", "code", "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(0, result)
        self.assertEqual("coding", payload["route"])

    def test_version(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stdout(output):
                main(["--version"])
        self.assertEqual(0, raised.exception.code)
        self.assertIn("Thrilla-zilla", output.getvalue())


if __name__ == "__main__":
    unittest.main()

