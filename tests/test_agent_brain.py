import unittest

from thrilla.brain import AgentBrain, BrainError


class AgentBrainTests(unittest.TestCase):
    def test_run_executes_observe_plan_act_verify_in_order(self):
        calls = []
        brain = AgentBrain(max_attempts=2)

        result = brain.run(
            goal="answer the owner",
            observe=lambda goal: calls.append(("observe", goal)) or {"ready": True},
            plan=lambda goal, observation, attempt: (
                calls.append(("plan", attempt)) or {"action": "answer"}
            ),
            act=lambda plan, attempt: calls.append(("act", attempt)) or "done",
            verify=lambda goal, outcome, observation: (
                calls.append(("verify", outcome)) or True
            ),
        )

        self.assertEqual(result.answer, "done")
        self.assertTrue(result.verified)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(
            [item[0] for item in calls],
            ["observe", "plan", "act", "verify"],
        )
        self.assertEqual(
            [event.phase for event in result.events],
            ["OBSERVE", "PLAN", "ACT", "VERIFY", "FINISH"],
        )

    def test_run_replans_after_failed_verification(self):
        attempts = []
        brain = AgentBrain(max_attempts=2)

        result = brain.run(
            goal="finish",
            observe=lambda goal: {"goal": goal},
            plan=lambda goal, observation, attempt: {"attempt": attempt},
            act=lambda plan, attempt: (
                attempts.append(attempt)
                or ("" if attempt == 1 else "verified result")
            ),
            verify=lambda goal, outcome, observation: bool(outcome),
        )

        self.assertEqual(attempts, [1, 2])
        self.assertEqual(result.answer, "verified result")
        self.assertEqual(result.attempts, 2)
        self.assertTrue(result.verified)

    def test_run_raises_after_verification_budget_is_exhausted(self):
        brain = AgentBrain(max_attempts=2)
        with self.assertRaises(BrainError):
            brain.run(
                goal="never verifies",
                observe=lambda goal: {},
                plan=lambda goal, observation, attempt: {},
                act=lambda plan, attempt: "",
                verify=lambda goal, outcome, observation: False,
            )

    def test_run_answer_wraps_one_autonomous_answer_action(self):
        brain = AgentBrain(max_attempts=2)
        calls = []
        result = brain.run_answer(
            "owner goal",
            lambda: calls.append("act") or "answer",
        )
        self.assertEqual(result.answer, "answer")
        self.assertTrue(result.verified)
        self.assertEqual(calls, ["act"])


if __name__ == "__main__":
    unittest.main()
