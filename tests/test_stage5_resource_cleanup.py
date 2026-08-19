"""Stage 5 final local-resource lifecycle gates."""

import gc
import tempfile
import unittest
import warnings
from pathlib import Path

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage5ResourceLifecycleTests(unittest.TestCase):
    def make_config(self, root):
        config = Config.defaults()
        config.state_root = root
        config.donor_root = str(Path(root) / "donors")
        config.owner_name = "Stage5 Tester"
        return config

    def test_close_is_idempotent_and_releases_memory(self):
        with tempfile.TemporaryDirectory() as root:
            app = ThrillaApp(self.make_config(root))
            app.memory.store.count()
            self.assertIsNotNone(app.memory.store._connection)
            app.close()
            app.close()
            self.assertIsNone(app.memory.store._connection)

    def test_garbage_collection_does_not_leave_sqlite_resource_warning(self):
        with tempfile.TemporaryDirectory() as root:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                app = ThrillaApp(self.make_config(root))
                app.memory.store.count()
                app.close()
                del app
                gc.collect()

            resource_warnings = [
                item
                for item in caught
                if issubclass(item.category, ResourceWarning)
            ]
            self.assertEqual(resource_warnings, [])


if __name__ == "__main__":
    unittest.main()
