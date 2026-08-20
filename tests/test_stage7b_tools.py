import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.tools import build_default_tool_executor


class Stage7BToolTests(unittest.TestCase):
    def make_executor(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        root = Path(temp.name)
        repo = root / "repo"
        state = root / "state"
        donors = root / "donors"

        for path in (repo, state, donors):
            path.mkdir()

        executor = build_default_tool_executor(
            repo,
            state,
            donors,
        )

        return root, repo, state, donors, executor

    def test_stage7b_registers_expanded_tool_surface(self):
        _, _, _, _, executor = self.make_executor()

        expected = {
            "file.read_text",
            "file.list",
            "file.search_text",
            "file.stat",
            "file.glob",
            "file.hash",
            "system.info",
            "process.run",
            "process.which",
            "git.status",
            "git.diff",
            "python.unittest",
        }

        self.assertEqual(
            set(executor.registry.names),
            expected,
        )

    def test_registry_catalog_exposes_permission_and_description(self):
        _, _, _, _, executor = self.make_executor()

        catalog = executor.registry.catalog

        self.assertEqual(
            len(catalog),
            len(executor.registry.names),
        )

        by_name = {
            item["name"]: item
            for item in catalog
        }

        self.assertEqual(
            by_name["file.stat"]["permission"],
            "READ",
        )

        self.assertTrue(
            by_name["python.unittest"]["description"]
        )

    def test_file_stat_returns_structured_metadata(self):
        _, repo, _, _, executor = self.make_executor()

        target = repo / "alpha.txt"
        target.write_text(
            "hello",
            encoding="utf-8",
        )

        result = executor.execute(
            "file.stat",
            {"path": str(target)},
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.output["size"],
            5,
        )
        self.assertEqual(
            result.output["type"],
            "file",
        )
        self.assertEqual(
            result.evidence[0].source,
            str(target.resolve()),
        )

    def test_file_glob_is_bounded_to_allowed_root(self):
        _, repo, _, _, executor = self.make_executor()

        package = repo / "thrilla"
        package.mkdir()

        one = package / "one.py"
        two = package / "two.py"
        note = package / "note.txt"

        one.write_text("1", encoding="utf-8")
        two.write_text("2", encoding="utf-8")
        note.write_text("x", encoding="utf-8")

        result = executor.execute(
            "file.glob",
            {
                "path": str(repo),
                "pattern": "**/*.py",
            },
        )

        self.assertTrue(result.ok)

        paths = {
            item["path"]
            for item in result.output["matches"]
        }

        self.assertEqual(
            paths,
            {
                str(one.resolve()),
                str(two.resolve()),
            },
        )

    def test_file_hash_returns_sha256(self):
        _, repo, _, _, executor = self.make_executor()

        target = repo / "payload.bin"
        target.write_bytes(b"abc")

        result = executor.execute(
            "file.hash",
            {"path": str(target)},
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.output["sha256"],
            hashlib.sha256(b"abc").hexdigest(),
        )

    def test_git_status_and_diff_are_dedicated_read_tools(self):
        _, repo, _, _, executor = self.make_executor()

        subprocess.run(
            ["git", "init", "-q"],
            cwd=str(repo),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=str(repo),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Thrilla Test"],
            cwd=str(repo),
            check=True,
        )

        target = repo / "sample.txt"
        target.write_text(
            "before\n",
            encoding="utf-8",
        )

        subprocess.run(
            ["git", "add", "sample.txt"],
            cwd=str(repo),
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "initial"],
            cwd=str(repo),
            check=True,
        )

        target.write_text(
            "after\n",
            encoding="utf-8",
        )

        status = executor.execute(
            "git.status",
            {"cwd": str(repo)},
        )
        diff = executor.execute(
            "git.diff",
            {"cwd": str(repo)},
        )

        self.assertTrue(status.ok)
        self.assertIn(
            "sample.txt",
            status.output["stdout"],
        )

        self.assertTrue(diff.ok)
        self.assertIn(
            "-before",
            diff.output["stdout"],
        )
        self.assertIn(
            "+after",
            diff.output["stdout"],
        )

    def test_process_which_finds_python_runtime(self):
        _, _, _, _, executor = self.make_executor()

        executable = Path(sys.executable).name

        result = executor.execute(
            "process.which",
            {"name": executable},
        )

        self.assertTrue(result.ok)
        self.assertTrue(
            result.output["path"]
        )

    def test_python_unittest_runs_bounded_repository_tests(self):
        _, repo, _, _, executor = self.make_executor()

        tests = repo / "tests"
        tests.mkdir()

        (tests / "test_sample.py").write_text(
            "import unittest\n"
            "\n"
            "class SampleTests(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(2 + 2, 4)\n",
            encoding="utf-8",
        )

        result = executor.execute(
            "python.unittest",
            {
                "cwd": str(repo),
                "mode": "discover",
                "start_dir": "tests",
                "pattern": "test_*.py",
                "timeout": 30,
            },
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            result.output["returncode"],
            0,
        )

        combined = (
            result.output["stdout"]
            + result.output["stderr"]
        )

        self.assertIn(
            "OK",
            combined,
        )


if __name__ == "__main__":
    unittest.main()
