import json
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.release_stage import (
    ReleaseStageError,
    UpdateLock,
    activate_release,
    build_plan,
    current_release,
    previous_release,
    rollback_release,
    stage_candidate,
    validate_release,
)


class ReleaseManagerTests(unittest.TestCase):
    def make_project(self, root: Path, version: str = "test") -> Path:
        project = root / "project"
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

    def staged(self, root: Path, name: str, version: str):
        project = self.make_project(root / name, version)
        state = root / "state"

        plan = build_plan(
            project,
            state,
            commit=name,
            timestamp=f"20260813-{name}",
        )
        stage_candidate(plan)
        return plan

    def test_validate_release_marks_candidate_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.staged(root, "one", "1.0")

            result = validate_release(plan, python_executable=sys.executable)

            self.assertTrue(result["validated"])
            self.assertTrue(result["compile_passed"])
            self.assertTrue(result["tests_passed"])

            manifest = json.loads(
                plan.manifest_path.read_text(encoding="utf-8")
            )
            self.assertEqual("validated", manifest["status"])
            self.assertTrue(manifest["tests_executed"])

    def test_failed_validation_never_activates_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.staged(root, "broken", "1.0")

            broken_test = plan.payload_dir / "tests" / "test_smoke.py"
            broken_test.write_text(
                "import unittest\n"
                "\n"
                "class Broken(unittest.TestCase):\n"
                "    def test_broken(self):\n"
                "        self.fail('expected failure')\n",
                encoding="utf-8",
            )

            with self.assertRaises(ReleaseStageError):
                validate_release(plan, python_executable=sys.executable)

            self.assertIsNone(current_release(plan.state_root))

    def test_first_activation_sets_current_without_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.staged(root, "one", "1.0")
            validate_release(plan, python_executable=sys.executable)

            activate_release(
                plan,
                python_executable=sys.executable,
            )

            self.assertEqual(
                plan.release_id,
                current_release(plan.state_root),
            )
            self.assertIsNone(previous_release(plan.state_root))

    def test_second_activation_preserves_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            first = self.staged(root, "one", "1.0")
            validate_release(first, python_executable=sys.executable)
            activate_release(first, python_executable=sys.executable)

            second = self.staged(root, "two", "2.0")
            validate_release(second, python_executable=sys.executable)
            activate_release(second, python_executable=sys.executable)

            self.assertEqual(
                second.release_id,
                current_release(second.state_root),
            )
            self.assertEqual(
                first.release_id,
                previous_release(second.state_root),
            )

    def test_failed_post_activation_proof_restores_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            first = self.staged(root, "one", "1.0")
            validate_release(first, python_executable=sys.executable)
            activate_release(first, python_executable=sys.executable)

            second = self.staged(root, "two", "2.0")
            validate_release(second, python_executable=sys.executable)

            # Break only the startup proof after validation.
            (second.payload_dir / "thrilla" / "__main__.py").write_text(
                "raise SystemExit(7)\n",
                encoding="utf-8",
            )

            with self.assertRaises(ReleaseStageError):
                activate_release(
                    second,
                    python_executable=sys.executable,
                )

            self.assertEqual(
                first.release_id,
                current_release(second.state_root),
            )

    def test_explicit_rollback_swaps_current_and_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            first = self.staged(root, "one", "1.0")
            validate_release(first, python_executable=sys.executable)
            activate_release(first, python_executable=sys.executable)

            second = self.staged(root, "two", "2.0")
            validate_release(second, python_executable=sys.executable)
            activate_release(second, python_executable=sys.executable)

            rollback_release(second.state_root)

            self.assertEqual(
                first.release_id,
                current_release(second.state_root),
            )
            self.assertEqual(
                second.release_id,
                previous_release(second.state_root),
            )

    def test_update_lock_rejects_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"

            with UpdateLock(state):
                with self.assertRaises(ReleaseStageError):
                    with UpdateLock(state):
                        pass


if __name__ == "__main__":
    unittest.main()
