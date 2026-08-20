import tempfile
import unittest

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage7EAppWiringTests(unittest.TestCase):
    def test_app_exposes_integrated_tools_to_autonomy(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = root
            config.donor_root = root

            app = ThrillaApp(config)
            self.addCleanup(app.close)

            registry_names = set(
                app.tool_executor.registry.names
            )

            for name in (
                "research.query",
                "memory.search",
                "memory.remember",
                "coding.repair",
            ):
                self.assertIn(
                    name,
                    registry_names,
                )

            autonomous_names = {
                item["name"]
                for item in app.autonomous_runner.tool_catalog
            }

            for name in (
                "research.query",
                "memory.search",
                "memory.remember",
                "coding.repair",
            ):
                self.assertIn(
                    name,
                    autonomous_names,
                )


if __name__ == "__main__":
    unittest.main()
