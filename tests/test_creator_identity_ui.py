import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from thrilla.app import ThrillaApp
from thrilla.config import Config


class CreatorIdentityUITests(unittest.TestCase):
    def make_app(self, owner):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        config.owner_name = owner
        app = ThrillaApp(config)
        app._header = Mock()
        app._pause = Mock()
        app._status = Mock()
        return app

    def status_values(self, app):
        app.about()
        return {
            args[0]: args[1]
            for args, _kwargs in app._status.call_args_list
            if len(args) >= 2
        }

    def test_about_identifies_permanent_creator(self):
        values = self.status_values(self.make_app("Alice"))
        self.assertEqual(values.get("Creator"), "Jesse James")

    def test_about_shows_owner_separately(self):
        values = self.status_values(self.make_app("Alice"))
        self.assertEqual(values.get("Creator"), "Jesse James")
        self.assertEqual(values.get("Owner"), "Alice")

    def test_different_owner_never_changes_creator(self):
        first = self.status_values(self.make_app("Alice"))
        second = self.status_values(self.make_app("Bob"))
        self.assertEqual(first.get("Creator"), "Jesse James")
        self.assertEqual(second.get("Creator"), "Jesse James")
        self.assertNotEqual(first.get("Owner"), second.get("Owner"))

    def test_app_does_not_duplicate_creator_literal(self):
        source = Path("thrilla/app.py").read_text(encoding="utf-8")
        self.assertNotIn('"Jesse James"', source)
        self.assertNotIn("'Jesse James'", source)


if __name__ == "__main__":
    unittest.main()
