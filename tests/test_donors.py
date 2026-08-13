import tempfile
import unittest
from pathlib import Path

from thrilla.catalog import CORE_DONORS
from thrilla.donors import DonorRegistry


class DonorRegistryTests(unittest.TestCase):
    def test_missing_incomplete_and_ready_are_distinct(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second, third = CORE_DONORS[:3]
            (root / first.relative_path / ".git").mkdir(parents=True)
            (root / second.relative_path).mkdir(parents=True)
            registry = DonorRegistry(root)
            self.assertEqual("ready", registry.inspect(first).state)
            self.assertEqual("incomplete", registry.inspect(second).state)
            self.assertEqual("missing", registry.inspect(third).state)
            self.assertEqual((1, 100), registry.progress(1))

    def test_git_file_counts_as_worktree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = CORE_DONORS[0]
            path = root / donor.relative_path
            path.mkdir(parents=True)
            (path / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
            self.assertTrue(DonorRegistry(root).inspect(donor).present)


if __name__ == "__main__":
    unittest.main()

