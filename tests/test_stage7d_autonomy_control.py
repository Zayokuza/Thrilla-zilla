import json
import tempfile
import unittest
from pathlib import Path

from thrilla.autonomy import (
    AutonomousBudgetError,
    AutonomousTaskRunner,
)
from thrilla.tools import build_default_tool_executor


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, messages, route):
        self.calls.append(
            {
                "messages": messages,
                "route": route,
            }
        )

        if not self.responses:
            raise AssertionError(
                "scripted model exhausted"
            )

        return self.responses.pop(0)


class DirectiveContext:
    def __init__(self, directives=()):
        self.directives = list(directives)
        self.checkpoints = []

    def checkpoint(self, action, **kwargs):
        self.checkpoints.append(
            (action, kwargs)
        )

        if self.directives:
            return (
                self.directives.pop(0),
            )

        return ()


class Stage7DAutonomyControlTests(unittest.TestCase):
    def make_runner(
        self,
        planner,
        *,
        critic=None,
        max_steps=8,
        max_tool_calls=8,
        max_replans=3,
        max_tool_failures=3,
        max_protocol_errors=2,
        max_repeat_actions=2,
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

        return (
            repo,
            AutonomousTaskRunner(
                tool_executor=executor,
                planner=planner,
                critic=critic,
                workspace=repo,
                max_steps=max_steps,
                max_tool_calls=max_tool_calls,
                max_replans=max_replans,
                max_tool_failures=max_tool_failures,
                max_protocol_errors=max_protocol_errors,
                max_repeat_actions=max_repeat_actions,
            ),
        )

    def test_critic_can_reject_finish_and_force_replan(self):
        planner = ScriptedModel(
            [
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "I think it is fine.",
                    }
                ),
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "system.info",
                        "arguments": {},
                        "reason": "collect actual evidence",
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "Verified using system evidence.",
                    }
                ),
            ]
        )

        critic = ScriptedModel(
            [
                json.dumps(
                    {
                        "verdict": "replan",
                        "reason": "No tool evidence exists yet.",
                    }
                ),
                json.dumps(
                    {
                        "verdict": "accept",
                        "reason": "Evidence now supports completion.",
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            critic=critic,
        )

        result = runner.run(
            "Inspect the local system."
        )

        self.assertTrue(
            result.completed
        )
        self.assertEqual(
            result.replans,
            1,
        )
        self.assertEqual(
            result.critic_checks,
            2,
        )
        self.assertEqual(
            result.tool_calls,
            1,
        )
        self.assertIn(
            "verified",
            result.answer.lower(),
        )

    def test_protocol_error_is_recoverable_within_budget(self):
        planner = ScriptedModel(
            [
                "this is not json",
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "Recovered.",
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_protocol_errors=1,
        )

        result = runner.run(
            "Recover from planner formatting."
        )

        self.assertTrue(
            result.completed
        )
        self.assertEqual(
            result.protocol_errors,
            1,
        )

    def test_protocol_error_budget_is_enforced(self):
        planner = ScriptedModel(
            [
                "bad output one",
                "bad output two",
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_protocol_errors=1,
        )

        with self.assertRaisesRegex(
            AutonomousBudgetError,
            "protocol-error budget",
        ):
            runner.run(
                "Break protocol repeatedly."
            )

    def test_tool_failure_budget_is_enforced(self):
        planner = ScriptedModel(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.read_text",
                        "arguments": {
                            "path": "missing-one.txt",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "file.read_text",
                        "arguments": {
                            "path": "missing-two.txt",
                        },
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_tool_failures=1,
        )

        with self.assertRaisesRegex(
            AutonomousBudgetError,
            "tool-failure budget",
        ):
            runner.run(
                "Read files that do not exist."
            )

    def test_tool_call_budget_is_separate_from_step_budget(self):
        planner = ScriptedModel(
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
                        "tool": "git.status",
                        "arguments": {},
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_steps=8,
            max_tool_calls=1,
        )

        with self.assertRaisesRegex(
            AutonomousBudgetError,
            "tool-call budget",
        ):
            runner.run(
                "Run too many tools."
            )

    def test_repeated_action_is_blocked_and_replanned(self):
        same = json.dumps(
            {
                "action": "tool",
                "tool": "system.info",
                "arguments": {},
            }
        )

        planner = ScriptedModel(
            [
                same,
                same,
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "Stopped repeating.",
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            max_repeat_actions=1,
            max_replans=2,
        )

        result = runner.run(
            "Avoid loops."
        )

        self.assertEqual(
            result.tool_calls,
            1,
        )
        self.assertEqual(
            result.loop_blocks,
            1,
        )
        self.assertEqual(
            result.replans,
            1,
        )

    def test_replan_budget_prevents_endless_critic_rejection(self):
        planner = ScriptedModel(
            [
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "finish one",
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "finish two",
                    }
                ),
            ]
        )

        critic = ScriptedModel(
            [
                json.dumps(
                    {
                        "verdict": "replan",
                        "reason": "not enough evidence",
                    }
                ),
                json.dumps(
                    {
                        "verdict": "replan",
                        "reason": "still not enough",
                    }
                ),
            ]
        )

        _, runner = self.make_runner(
            planner,
            critic=critic,
            max_replans=1,
        )

        with self.assertRaisesRegex(
            AutonomousBudgetError,
            "replan budget",
        ):
            runner.run(
                "Do not falsely finish."
            )

    def test_tool_failures_are_classified(self):
        planner = ScriptedModel(
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
                        "answer": "The file is missing.",
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

        self.assertEqual(
            result.steps[0].failure_kind,
            "missing",
        )

    def test_owner_directive_reaches_next_plan(self):
        planner = ScriptedModel(
            [
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "Directive received.",
                    }
                )
            ]
        )

        _, runner = self.make_runner(
            planner
        )

        context = DirectiveContext(
            directives=(
                "Focus only on local evidence",
            )
        )

        runner.run(
            "Inspect this.",
            job_context=context,
        )

        prompt = (
            planner.calls[0]
            ["messages"][-1]
            ["content"]
        )

        self.assertIn(
            "Focus only on local evidence",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
