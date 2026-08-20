import json
import tempfile
import unittest
from pathlib import Path

from thrilla.autonomy import (
    AutonomousProtocolError,
    AutonomousTaskRunner,
)
from thrilla.tools import build_default_tool_executor


class ScriptedPlanner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, messages, route):
        self.calls.append(
            (
                messages,
                route,
            )
        )

        if not self.responses:
            raise AssertionError(
                "planner called more times than expected"
            )

        return self.responses.pop(0)


class Stage7CAutonomyTests(unittest.TestCase):
    def make_runner(
        self,
        planner,
        *,
        max_steps=8,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        root = Path(temp.name)
        repo = root / "repo"
        state = root / "state"
        donors = root / "donors"

        for path in (
            repo,
            state,
            donors,
        ):
            path.mkdir()

        executor = build_default_tool_executor(
            repo,
            state,
            donors,
        )

        runner = AutonomousTaskRunner(
            tool_executor=executor,
            planner=planner,
            workspace=repo,
            max_steps=max_steps,
        )

        return repo, runner

    def test_runner_chains_tools_until_finish(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.read_text",
                        "arguments": {
                            "path": "note.txt",
                        },
                        "reason": "inspect evidence",
                    }
                ),
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.hash",
                        "arguments": {
                            "path": "note.txt",
                        },
                        "reason": "verify identity",
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": (
                            "The file was read and its "
                            "SHA-256 identity was verified."
                        ),
                    }
                ),
            ]
        )

        repo, runner = self.make_runner(
            planner
        )

        (repo / "note.txt").write_text(
            "verified autonomous evidence\n",
            encoding="utf-8",
        )

        result = runner.run(
            "Inspect note.txt and verify it."
        )

        self.assertTrue(result.completed)

        self.assertEqual(
            result.tool_calls,
            2,
        )

        self.assertEqual(
            len(result.steps),
            2,
        )

        self.assertEqual(
            result.steps[0].tool,
            "file.read_text",
        )

        self.assertEqual(
            result.steps[1].tool,
            "file.hash",
        )

        self.assertTrue(
            result.steps[0].ok
        )

        self.assertTrue(
            result.steps[1].ok
        )

        self.assertIn(
            "verified",
            result.answer.lower(),
        )

    def test_relative_paths_are_resolved_inside_workspace(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.stat",
                        "arguments": {
                            "path": "sub/data.txt",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "done",
                    }
                ),
            ]
        )

        repo, runner = self.make_runner(
            planner
        )

        sub = repo / "sub"
        sub.mkdir()

        target = sub / "data.txt"
        target.write_text(
            "abc",
            encoding="utf-8",
        )

        result = runner.run(
            "Inspect sub/data.txt"
        )

        observed = (
            result.steps[0]
            .output["source"]
        )

        self.assertEqual(
            observed,
            str(target.resolve()),
        )

    def test_unknown_tool_is_rejected_before_execution(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "danger.destroy",
                        "arguments": {},
                    }
                )
            ]
        )

        _, runner = self.make_runner(
            planner
        )

        with self.assertRaises(
            AutonomousProtocolError
        ):
            runner.run(
                "Destroy everything"
            )

    def test_planner_cannot_request_write_or_network_permissions(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.read_text",
                        "arguments": {
                            "path": "missing.txt",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "finished",
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner
        )

        allowed = {
            item["permission"]
            for item in runner.tool_catalog
        }

        self.assertNotIn(
            "WRITE",
            allowed,
        )

        self.assertNotIn(
            "NETWORK",
            allowed,
        )

    def test_failed_tool_result_returns_to_planner(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.read_text",
                        "arguments": {
                            "path": "missing.txt",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": (
                            "The requested file does not exist."
                        ),
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner
        )

        result = runner.run(
            "Read missing.txt"
        )

        self.assertFalse(
            result.steps[0].ok
        )

        self.assertTrue(
            result.completed
        )

        second_prompt = (
            planner.calls[1][0][-1]["content"]
        )

        self.assertIn(
            "missing",
            second_prompt.lower(),
        )

    def test_runner_enforces_step_ceiling(self):
        planner = ScriptedPlanner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "system.info",
                        "arguments": {},
                    }
                ),
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "system.info",
                        "arguments": {},
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_steps=2,
        )

        with self.assertRaisesRegex(
            AutonomousProtocolError,
            "step limit",
        ):
            runner.run(
                "Keep inspecting forever"
            )

    def test_fenced_json_planner_output_is_accepted(self):
        planner = ScriptedPlanner(
            [
                """```json
{
  "action": "finish",
  "answer": "complete"
}
```"""
            ]
        )

        _, runner = self.make_runner(
            planner
        )

        result = runner.run(
            "Simple task"
        )

        self.assertEqual(
            result.answer,
            "complete",
        )


if __name__ == "__main__":
    unittest.main()
