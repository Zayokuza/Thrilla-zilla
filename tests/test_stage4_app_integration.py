import tempfile
import unittest
from pathlib import Path

from thrilla.app import ThrillaApp
from thrilla.config import Config


class Stage4AppIntegrationTests(unittest.TestCase):
    def make_app(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        config = Config.defaults()
        config.state_root = str(
            Path(temp.name) / "state"
        )
        config.donor_root = str(
            Path(temp.name) / "donors"
        )
        Path(config.donor_root).mkdir(
            parents=True
        )

        return ThrillaApp(config)

    def test_owner_memory_direct_answer_bypasses_model(self):
        app = self.make_app()

        app.memory.remember_explicit(
            "My name is Jesse"
        )

        def fail_chat(messages, route):
            raise AssertionError(
                "owner memory query must not call the model"
            )

        app.runtime_supervisor.chat = fail_chat

        answer = app._resolve_ask_answer(
            "what is my name",
            [],
            "general-chat",
        )

        self.assertEqual(
            answer,
            "Your name is Jesse.",
        )

    def test_self_knowledge_direct_answer_bypasses_model(self):
        app = self.make_app()

        def fail_chat(messages, route):
            raise AssertionError(
                "self-knowledge query must not call the model"
            )

        app.runtime_supervisor.chat = fail_chat

        answer = app._resolve_ask_answer(
            "what can you do",
            [],
            "general-chat",
        )

        self.assertIn(
            "Roadmap stage: 4/6",
            answer,
        )

    def test_automatic_name_memory_updates_configured_owner(self):
        app = self.make_app()

        facts = app.memory.observe(
            "My name is Jesse"
        )
        app._sync_owner_name(facts)

        self.assertEqual(
            app.config.owner_name,
            "Jesse",
        )


if __name__ == "__main__":
    unittest.main()
