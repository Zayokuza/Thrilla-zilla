import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.cli import main
from thrilla.release_stage import (
    ReleaseStageError,
    UpdateLock,
    install_release,
    prune_releases,
    rollback_release,
)


class ReleaseControlTests(unittest.TestCase):
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
            "class Smoke(unittest.TestCase):\n"
            "    def test_smoke(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        return project

    def test_stale_update_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            state.mkdir()

            lock = state / "update.lock"
            lock.write_text("99999999\n", encoding="utf-8")

            with UpdateLock(state):
                self.assertTrue(lock.exists())

            self.assertFalse(lock.exists())

    def test_live_update_lock_is_never_stolen(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            state.mkdir()

            lock = state / "update.lock"
            lock.write_text(f"{os.getpid()}\n", encoding="utf-8")

            with self.assertRaises(ReleaseStageError):
                with UpdateLock(state):
                    pass

    def test_rollback_obeys_release_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"

            with UpdateLock(state):
                with self.assertRaises(ReleaseStageError):
                    rollback_release(
                        state,
                        python_executable=sys.executable,
                    )

    def test_prune_obeys_release_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"

            with UpdateLock(state):
                with self.assertRaises(ReleaseStageError):
                    prune_releases(state, keep_newest=1)

    def test_release_status_cli_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "release",
                    "status",
                    "--state-root",
                    str(state),
                    "--json",
                ])

            self.assertEqual(0, result)

            payload = json.loads(output.getvalue())
            self.assertIsNone(payload["current"])
            self.assertIsNone(payload["previous"])
            self.assertEqual([], payload["releases"])

    def test_release_rollback_cli_changes_active_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            first = self.make_project(root / "one", "1.0")
            second = self.make_project(root / "two", "2.0")

            install_release(
                first,
                state,
                commit="111111111111",
                timestamp="20260813-180001",
                python_executable=sys.executable,
            )
            install_release(
                second,
                state,
                commit="222222222222",
                timestamp="20260813-180002",
                python_executable=sys.executable,
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([
                    "release",
                    "rollback",
                    "--state-root",
                    str(state),
                    "--json",
                ])

            self.assertEqual(0, result)

            payload = json.loads(output.getvalue())
            self.assertEqual(
                "20260813-180001-111111111111",
                payload["current"],
            )


if __name__ == "__main__":
    unittest.main()
