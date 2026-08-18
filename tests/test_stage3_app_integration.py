import tempfile
import unittest
from pathlib import Path

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage3AppIntegrationTests(unittest.TestCase):
    def make_app(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config = Config.defaults()
        config.state_root = str(Path(temp.name) / "state")
        config.donor_root = str(Path(temp.name) / "donors")
        Path(config.donor_root).mkdir(parents=True)
        return ThrillaApp(config)

    def test_app_has_autonomous_coding_agent(self):
        app = self.make_app()
        self.assertTrue(hasattr(app, "coding_agent"))
        self.assertEqual(
            app.coding_agent.repo_root,
            Path(__file__).resolve().parent.parent,
        )

    def test_self_repair_intent_is_narrow(self):
        app = self.make_app()
        self.assertTrue(app._is_self_repair_request("fix yourself"))
        self.assertTrue(app._is_self_repair_request("fix itself"))
        self.assertTrue(app._is_self_repair_request("repair Thrilla itself"))
        self.assertFalse(app._is_self_repair_request("fix my Python example"))


if __name__ == "__main__":
    unittest.main()
