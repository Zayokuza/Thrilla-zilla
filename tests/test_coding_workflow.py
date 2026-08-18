import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from thrilla.coding import (
    AutonomousCodingAgent,
    CodingPlanError,
    FileEdit,
    RepositoryCodingWorkflow,
)


class CodingWorkflowTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        repo = root / "repo"
        state = root / "state"
        repo.mkdir()
        state.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
        (repo / "thrilla").mkdir()
        (repo / "tests").mkdir()
        return repo, state

    def test_verified_edit_is_kept(self):
        repo, state = self.make_repo()
        target = repo / "thrilla" / "value.py"
        target.write_text("VALUE = 1\n", encoding="utf-8")

        workflow = RepositoryCodingWorkflow(repo, state)
        outcome = workflow.apply_edits(
            "change VALUE to 2",
            (FileEdit("thrilla/value.py", "VALUE = 2\n"),),
            ((sys.executable, "-m", "py_compile", "thrilla/value.py"),),
        )

        self.assertTrue(outcome.ok)
        self.assertFalse(outcome.rolled_back)
        self.assertEqual(target.read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertTrue(outcome.critic.passed)

    def test_failed_verification_rolls_back_exact_content(self):
        repo, state = self.make_repo()
        target = repo / "thrilla" / "value.py"
        original = "VALUE = 1\n"
        target.write_text(original, encoding="utf-8")

        workflow = RepositoryCodingWorkflow(repo, state)
        outcome = workflow.apply_edits(
            "break for rollback test",
            (FileEdit("thrilla/value.py", "VALUE = (\n"),),
            ((sys.executable, "-m", "py_compile", "thrilla/value.py"),),
        )

        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.rolled_back)
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_model_plan_can_drive_verified_edit(self):
        repo, state = self.make_repo()
        target = repo / "thrilla" / "sample.py"
        target.write_text("VALUE = 10\n", encoding="utf-8")

        def fake_model(messages, route):
            self.assertEqual(route, "coding")
            self.assertIn("thrilla/sample.py", messages[-1]["content"])
            return json.dumps(
                {
                    "summary": "raise the value",
                    "edits": [
                        {
                            "path": "thrilla/sample.py",
                            "old": "VALUE = 10\n",
                            "new": "VALUE = 11\n",
                        }
                    ],
                }
            )

        agent = AutonomousCodingAgent(repo, state, fake_model)
        outcome = agent.run(
            "raise VALUE",
            ((sys.executable, "-m", "py_compile", "thrilla/sample.py"),),
            ("thrilla/sample.py",),
        )

        self.assertTrue(outcome.ok)
        self.assertEqual(target.read_text(encoding="utf-8"), "VALUE = 11\n")

    def test_model_cannot_edit_uninspected_path(self):
        repo, state = self.make_repo()
        allowed = repo / "thrilla" / "allowed.py"
        blocked = repo / "thrilla" / "blocked.py"
        allowed.write_text("VALUE = 1\n", encoding="utf-8")
        blocked.write_text("SECRET = 1\n", encoding="utf-8")

        def fake_model(messages, route):
            return json.dumps(
                {
                    "summary": "wrong path",
                    "edits": [
                        {
                            "path": "thrilla/blocked.py",
                            "old": "SECRET = 1\n",
                            "new": "SECRET = 2\n",
                        }
                    ],
                }
            )

        agent = AutonomousCodingAgent(repo, state, fake_model)

        with self.assertRaises(CodingPlanError):
            agent.run(
                "edit allowed only",
                ((sys.executable, "-m", "py_compile", "thrilla/allowed.py"),),
                ("thrilla/allowed.py",),
            )

        self.assertEqual(blocked.read_text(encoding="utf-8"), "SECRET = 1\n")


if __name__ == "__main__":
    unittest.main()
