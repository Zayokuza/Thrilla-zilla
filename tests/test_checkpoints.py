import tempfile
import unittest
from pathlib import Path

from thrilla.checkpoints import CheckpointError, CheckpointManager


class CheckpointManagerTests(unittest.TestCase):
    def test_rollback_restores_existing_and_removes_new_file(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            repo = root / "repo"
            state = root / "state"
            repo.mkdir()
            state.mkdir()

            existing = repo / "existing.py"
            existing.write_text("before = 1\n", encoding="utf-8")

            manager = CheckpointManager(repo, state)
            checkpoint = manager.create(("existing.py", "new_file.py"))

            existing.write_text("after = 2\n", encoding="utf-8")
            new_file = repo / "new_file.py"
            new_file.write_text("created = True\n", encoding="utf-8")

            manager.rollback(checkpoint)

            self.assertEqual(
                existing.read_text(encoding="utf-8"),
                "before = 1\n",
            )
            self.assertFalse(new_file.exists())
            self.assertTrue((checkpoint.directory / "manifest.json").is_file())

    def test_checkpoint_rejects_repository_escape(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            repo = root / "repo"
            state = root / "state"
            repo.mkdir()
            state.mkdir()

            manager = CheckpointManager(repo, state)

            with self.assertRaises(CheckpointError):
                manager.create(("../outside.py",))


if __name__ == "__main__":
    unittest.main()
