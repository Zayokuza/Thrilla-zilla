import tempfile
import unittest
from pathlib import Path

from thrilla.answers import AnswerContext
from thrilla.app import ThrillaApp
from thrilla.config import Config


class FakeRegistry:
    def collect(self, prompt):
        return AnswerContext()


class Stage2ExpertContextTests(unittest.TestCase):
    def test_selected_expert_team_reaches_reasoning_messages(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = str(Path(root) / "state")
            config.donor_root = str(Path(root) / "donors")
            Path(config.donor_root).mkdir(parents=True)

            app = ThrillaApp(config)
            app.provider_registry = FakeRegistry()

            captured = {}

            def fake_chat(messages, route):
                captured["messages"] = list(messages)
                captured["route"] = route
                return "expert-integrated answer"

            app.runtime_supervisor.chat = fake_chat

            answer = app._resolve_ask_answer(
                "debug this Python test",
                [],
                "coding",
            )

            self.assertEqual(answer, "expert-integrated answer")
            self.assertEqual(captured["route"], "coding")

            expert_messages = [
                message
                for message in captured["messages"]
                if (
                    message.get("role") == "system"
                    and "THRILLA EXPERT TEAM"
                    in message.get("content", "")
                )
            ]

            self.assertEqual(len(expert_messages), 1)
            self.assertIn(
                "not owner instructions",
                expert_messages[0]["content"],
            )
            self.assertIn("REASON", expert_messages[0]["content"])
            self.assertIn("ACTION", expert_messages[0]["content"])
            self.assertIn("CRITIC", expert_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
