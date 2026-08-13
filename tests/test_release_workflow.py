import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.release_stage import (
    install_release,
    prune_releases,
    release_status,
    rollback_release,
    write_posix_launcher,
    write_windows_launcher,
)


class ReleaseWorkflowTests(unittest.TestCase):
    def make_project(self, root: Path, version: str) -> Path:
        project = root
        (project / "thrilla").mkdir(parents=True)
        (project / "tests").mkdir()

        (project / "thrilla" / "__init__.py").write_text(
            f'__version__ = "{version}"\n',
            encoding="utf-8",
        )

        (project / "thrilla" / "__main__.py").write_text(
            "from thrilla import __version__\n"
            "print(__version__)\n",
            encoding="utf-8",
        )

        (project / "tests" / "test_smoke.py").write_text(
            "import unittest\n"
            "\n"
            "class Smoke(unittest.TestCase):\n"
            "    def test_smoke(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        return project

    def test_install_release_stages_validates_and_activates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            project = self.make_project(root / "source", "1.0")

            manifest = install_release(
                project,
                state,
                commit="abcdef123456",
                timestamp="20260813-170001",
                python_executable=sys.executable,
            )

            self.assertEqual("active", manifest["status"])

            status = release_status(state)
            self.assertEqual(
                "20260813-170001-abcdef123456",
                status["current"],
            )
            self.assertIsNone(status["previous"])

    @unittest.skipUnless(shutil.which("bash"), "bash required")
    def test_stable_posix_launcher_follows_release_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            first = self.make_project(root / "one", "1.0")
            second = self.make_project(root / "two", "2.0")

            install_release(
                first,
                state,
                commit="111111111111",
                timestamp="20260813-170002",
                python_executable=sys.executable,
            )
            install_release(
                second,
                state,
                commit="222222222222",
                timestamp="20260813-170003",
                python_executable=sys.executable,
            )

            launcher = root / "bin" / "thrilla"

            write_posix_launcher(
                launcher,
                state,
                python_executable=sys.executable,
            )

            result = subprocess.run(
                [str(launcher), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=10,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("2.0", result.stdout.strip())

            rollback_release(
                state,
                python_executable=sys.executable,
            )

            result = subprocess.run(
                [str(launcher), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=10,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("1.0", result.stdout.strip())

    def test_release_status_lists_current_previous_and_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            first = self.make_project(root / "one", "1.0")
            second = self.make_project(root / "two", "2.0")

            install_release(
                first,
                state,
                commit="111111111111",
                timestamp="20260813-170004",
                python_executable=sys.executable,
            )

            install_release(
                second,
                state,
                commit="222222222222",
                timestamp="20260813-170005",
                python_executable=sys.executable,
            )

            status = release_status(state)

            self.assertEqual(
                "20260813-170005-222222222222",
                status["current"],
            )
            self.assertEqual(
                "20260813-170004-111111111111",
                status["previous"],
            )
            self.assertEqual(2, len(status["releases"]))

    def test_prune_preserves_current_previous_and_newest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            for index in range(5):
                project = self.make_project(
                    root / f"project-{index}",
                    str(index),
                )
                install_release(
                    project,
                    state,
                    commit=f"{index}" * 12,
                    timestamp=f"20260813-17010{index}",
                    python_executable=sys.executable,
                )

            before = release_status(state)

            current = before["current"]
            previous = before["previous"]

            removed = prune_releases(
                state,
                keep_newest=1,
            )

            after = release_status(state)
            remaining = {
                item["release_id"]
                for item in after["releases"]
            }

            self.assertIn(current, remaining)
            self.assertIn(previous, remaining)
            self.assertGreater(len(removed), 0)

    def test_windows_launcher_uses_current_release_pointer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            launcher = root / "thrilla.cmd"

            write_windows_launcher(
                launcher,
                state,
                python_executable="python",
            )

            text = launcher.read_text(encoding="utf-8")

            self.assertIn("current", text)
            self.assertIn("releases", text)
            self.assertIn("PYTHONPATH", text)
            self.assertIn("-m thrilla", text)


if __name__ == "__main__":
    unittest.main()
