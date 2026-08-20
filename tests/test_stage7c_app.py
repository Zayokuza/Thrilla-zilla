import tempfile
import unittest

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage7CAppTests(unittest.TestCase):
    def test_app_constructs_general_autonomous_runner(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = root
            config.donor_root = root
            config.owner_name = "Owner"

            app = ThrillaApp(
                config
            )

            self.addCleanup(
                app.close
            )

            self.assertTrue(
                hasattr(
                    app,
                    "autonomous_runner",
                )
            )

            self.assertIs(
                app.workflows.autonomous_runner,
                app.autonomous_runner,
            )


if __name__ == "__main__":
    unittest.main()
