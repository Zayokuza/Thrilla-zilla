import tempfile
import unittest
from pathlib import Path

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage2AppIntegrationTests(unittest.TestCase):
    def test_app_exposes_100_experts_and_structured_tools(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = str(Path(root) / "state")
            config.donor_root = str(Path(root) / "donors")
            Path(config.donor_root).mkdir(parents=True)
            app = ThrillaApp(config)
            self.assertEqual(
                len(app.expert_orchestrator.registry.experts),
                100,
            )
            self.assertIn("file.read_text", app.tool_executor.registry.names)
            self.assertIn("process.run", app.tool_executor.registry.names)


if __name__ == "__main__":
    unittest.main()
