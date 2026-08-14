import json
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.release_stage import (
    ReleaseStageError,
    activate_release,
    build_plan,
    current_release,
    install_release,
    previous_release,
    stage_candidate,
    validate_release,
    write_posix_launcher,
)


class ReleaseSafetyTests(unittest.TestCase):
    def make_project(
        self,
        root: Path,
        version: str,
        failing: bool = False,
    ) -> Path:
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

        if failing:
            body = (
                "import unittest\n"
                "class Smoke(unittest.TestCase):\n"
                "    def test_smoke(self):\n"
                "        self.fail('expected failure')\n"
            )
        else:
            body = (
                "import unittest\n"
                "class Smoke(unittest.TestCase):\n"
                "    def test_smoke(self):\n"
                "        self.assertTrue(True)\n"
            )

        (project / "tests" / "test_smoke.py").write_text(
            body,
            encoding="utf-8",
        )

        return project

    def test_launcher_replaces_symlink_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            old_target = root / "old-source-launcher"
            old_target.write_text(
                "LEGACY SOURCE LAUNCHER\n",
                encoding="utf-8",
            )

            launcher = root / "bin" / "thrilla"
            launcher.parent.mkdir()
            launcher.symlink_to(old_target)

            write_posix_launcher(
                launcher,
                state,
                python_executable=sys.executable,
            )

            self.assertEqual(
                "LEGACY SOURCE LAUNCHER\n",
                old_target.read_text(encoding="utf-8"),
            )
            self.assertFalse(launcher.is_symlink())
            self.assertIn(
                "current",
                launcher.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "THRILLA_HOME",
                launcher.read_text(encoding="utf-8"),
            )

    def test_failed_third_activation_restores_prior_pointer_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            first = self.make_project(root / "one", "1")
            second = self.make_project(root / "two", "2")
            third = self.make_project(root / "three", "3")

            install_release(
                first,
                state,
                commit="111111111111",
                timestamp="20260813-190001",
                python_executable=sys.executable,
            )

            install_release(
                second,
                state,
                commit="222222222222",
                timestamp="20260813-190002",
                python_executable=sys.executable,
            )

            plan = build_plan(
                third,
                state,
                commit="333333333333",
                timestamp="20260813-190003",
            )
            stage_candidate(plan)
            validate_release(
                plan,
                python_executable=sys.executable,
            )

            (plan.payload_dir / "thrilla" / "__main__.py").write_text(
                "raise SystemExit(9)\n",
                encoding="utf-8",
            )

            with self.assertRaises(ReleaseStageError):
                activate_release(
                    plan,
                    python_executable=sys.executable,
                )

            self.assertEqual(
                "20260813-190002-222222222222",
                current_release(state),
            )
            self.assertEqual(
                "20260813-190001-111111111111",
                previous_release(state),
            )

    def test_successful_activation_marks_old_release_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            first = self.make_project(root / "one", "1")
            second = self.make_project(root / "two", "2")

            install_release(
                first,
                state,
                commit="111111111111",
                timestamp="20260813-190004",
                python_executable=sys.executable,
            )

            install_release(
                second,
                state,
                commit="222222222222",
                timestamp="20260813-190005",
                python_executable=sys.executable,
            )

            old_manifest = json.loads(
                (
                    state
                    / "releases"
                    / "20260813-190004-111111111111"
                    / "release.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                "previous",
                old_manifest["status"],
            )

    def test_failed_validation_preserves_existing_active_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"

            good = self.make_project(root / "good", "1")
            bad = self.make_project(
                root / "bad",
                "broken",
                failing=True,
            )

            install_release(
                good,
                state,
                commit="111111111111",
                timestamp="20260813-190006",
                python_executable=sys.executable,
            )

            before = current_release(state)

            with self.assertRaises(ReleaseStageError):
                install_release(
                    bad,
                    state,
                    commit="999999999999",
                    timestamp="20260813-190007",
                    python_executable=sys.executable,
                )

            self.assertEqual(
                before,
                current_release(state),
            )

    def test_installers_use_atomic_release_manager(self):
        root = Path(__file__).resolve().parents[1]

        termux = (root / "install-termux.sh").read_text(
            encoding="utf-8"
        )
        windows = (root / "install-windows.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "release install",
            termux,
        )
        self.assertNotIn(
            "ln -sfn",
            termux,
        )

        self.assertIn(
            "release install",
            windows,
        )


if __name__ == "__main__":
    unittest.main()
