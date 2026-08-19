"""Stage 5 Task 5/6 app construction tests."""

import tempfile
import unittest
from pathlib import Path

from thrilla.app import ThrillaApp
from thrilla.config import Config
from thrilla.jobs import JobManager
from thrilla.live_ui import LiveWorkRenderer
from thrilla.research import ResearchEngine
from thrilla.workflows import WorkflowServices


class Stage5AppIntegrationTests(unittest.TestCase):
    def make_config(self, root):
        config = Config.defaults()
        config.state_root = root
        config.donor_root = str(Path(root) / "donors")
        return config

    def test_app_constructs_live_background_services(self):
        with tempfile.TemporaryDirectory() as root:
            app = ThrillaApp(self.make_config(root))
            try:
                self.assertIsInstance(app.job_manager, JobManager)
                self.assertIsInstance(app.research_engine, ResearchEngine)
                self.assertIsInstance(app.workflows, WorkflowServices)
                self.assertIsInstance(app.live_renderer, LiveWorkRenderer)
            finally:
                app.close()

    def test_public_read_policy_uses_stage5_default(self):
        with tempfile.TemporaryDirectory() as root:
            app = ThrillaApp(self.make_config(root))
            try:
                self.assertTrue(app.network_policy.public_read_enabled)
                self.assertFalse(app.network_policy.write_enabled)
            finally:
                app.close()

    def test_close_releases_memory_connection(self):
        with tempfile.TemporaryDirectory() as root:
            app = ThrillaApp(self.make_config(root))
            app.memory.store.count()
            self.assertIsNotNone(app.memory.store._connection)
            app.close()
            self.assertIsNone(app.memory.store._connection)


if __name__ == "__main__":
    unittest.main()
