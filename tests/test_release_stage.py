import json
import tempfile
import unittest
from pathlib import Path

from thrilla.release_stage import (
    ReleaseStageError,
    build_plan,
    stage_candidate,
)


class ReleaseStageTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "project"
        (project / "thrilla").mkdir(parents=True)
        (project / "tests").mkdir()
        (project / ".git").mkdir()

        (project / "thrilla" / "__init__.py").write_text(
            '__version__ = "test"\n',
            encoding="utf-8",
        )
        (project / "tests" / "test_smoke.py").write_text(
            "value = 1\n",
            encoding="utf-8",
        )
        (project / "README.md").write_text(
            "candidate\n",
            encoding="utf-8",
        )
        (project / ".git" / "secret").write_text(
            "must not copy\n",
            encoding="utf-8",
        )
        return project

    def test_plan_uses_dated_release_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_project(root)
            state = root / "state"

            plan = build_plan(
                project,
                state,
                commit="abcdef1234567890",
                timestamp="20260813-060000",
            )

            self.assertEqual(
                state / "releases" / "20260813-060000-abcdef123456",
                plan.release_dir,
            )
            self.assertEqual(plan.release_dir / "payload", plan.payload_dir)
            self.assertEqual(
                plan.release_dir / "release.json",
                plan.manifest_path,
            )

    def test_stage_candidate_is_inactive_and_copies_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_project(root)
            state = root / "state"

            plan = build_plan(
                project,
                state,
                commit="abcdef123456",
                timestamp="20260813-060001",
            )

            manifest = stage_candidate(plan)

            self.assertTrue(
                (plan.payload_dir / "thrilla" / "__init__.py").is_file()
            )
            self.assertTrue(
                (plan.payload_dir / "tests" / "test_smoke.py").is_file()
            )
            self.assertFalse((plan.payload_dir / ".git").exists())

            self.assertEqual("staged-inactive", manifest["status"])
            self.assertFalse(manifest["activation_supported"])
            self.assertFalse(manifest["rollback_supported"])
            self.assertFalse(manifest["tests_executed"])

    def test_staging_never_touches_live_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_project(root)
            state = root / "state"

            live_bin = root / "live-bin"
            live_bin.mkdir()
            launcher = live_bin / "thrilla"
            launcher.write_text(
                "CURRENT WORKING THRILLA\n",
                encoding="utf-8",
            )

            before = launcher.read_bytes()

            plan = build_plan(
                project,
                state,
                commit="abcdef123456",
                timestamp="20260813-060002",
            )
            stage_candidate(plan)

            self.assertEqual(before, launcher.read_bytes())

    def test_manifest_is_written_atomically_with_candidate_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_project(root)
            state = root / "state"

            plan = build_plan(
                project,
                state,
                commit="abcdef123456",
                timestamp="20260813-060003",
            )
            stage_candidate(plan)

            payload = json.loads(
                plan.manifest_path.read_text(encoding="utf-8")
            )

            self.assertEqual("abcdef123456", payload["commit"])
            self.assertEqual(str(project.resolve()), payload["source"])
            self.assertEqual(
                str(plan.payload_dir.resolve()),
                payload["payload"],
            )

    def test_existing_release_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = self.make_project(root)
            state = root / "state"

            plan = build_plan(
                project,
                state,
                commit="abcdef123456",
                timestamp="20260813-060004",
            )

            stage_candidate(plan)

            with self.assertRaises(ReleaseStageError):
                stage_candidate(plan)


if __name__ == "__main__":
    unittest.main()
