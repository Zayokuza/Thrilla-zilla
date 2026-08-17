import tempfile
import unittest
from pathlib import Path

from thrilla.answers import (
    AnswerContext,
    Evidence,
    KnowledgeGap,
)
from thrilla.app import ThrillaApp
from thrilla.config import Config


class FakeRegistry:
    def __init__(self, context):
        self.context = context
        self.prompts = []

    def collect(self, prompt):
        self.prompts.append(prompt)
        return self.context


class FakeClient:
    def __init__(
        self,
        answer="model answer",
        events=None,
    ):
        self.answer = answer
        self.calls = []
        self.events = events

    def chat(self, messages, route):
        if self.events is not None:
            self.events.append("chat")

        self.calls.append(
            (messages, route)
        )

        return self.answer


class FakeBinding:
    def __init__(self, client):
        self.client = client


class FakeRuntimeManager:
    def __init__(
        self,
        client=None,
        events=None,
    ):
        self.client = client or FakeClient()
        self.events = events
        self.calls = []

    def ready_binding(
        self,
        model_url,
        expected_model,
    ):
        if self.events is not None:
            self.events.append(
                "ready_binding"
            )

        self.calls.append(
            (
                model_url,
                expected_model,
            )
        )

        return FakeBinding(
            self.client
        )


class ForbiddenRuntimeManager:
    def ready_binding(self, *args, **kwargs):
        raise AssertionError(
            "runtime must not be used"
        )


class UniversalAskTests(unittest.TestCase):
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

        return ThrillaApp(config)

    def test_arbitrary_question_reaches_reasoning_path(self):
        app = self.make_app()

        app.provider_registry = FakeRegistry(
            AnswerContext()
        )

        client = FakeClient(
            answer="general answer"
        )

        runtime = FakeRuntimeManager(
            client=client
        )

        app.runtime_manager = runtime

        answer = app._resolve_ask_answer(
            "Explain black holes.",
            [],
            "general-chat",
        )

        self.assertEqual(
            answer,
            "general answer",
        )

        self.assertEqual(
            len(runtime.calls),
            1,
        )

        self.assertEqual(
            client.calls[0][0][-1],
            {
                "role": "user",
                "content": (
                    "Explain black holes."
                ),
            },
        )

    def test_direct_provider_answer_bypasses_model(self):
        app = self.make_app()

        app.provider_registry = FakeRegistry(
            AnswerContext(
                direct_answer=(
                    "Observed deterministic answer."
                )
            )
        )

        app.runtime_manager = (
            ForbiddenRuntimeManager()
        )

        answer = app._resolve_ask_answer(
            "What time is it?",
            [],
            "general-chat",
        )

        self.assertEqual(
            answer,
            "Observed deterministic answer.",
        )

    def test_evidence_is_separate_from_owner_request(self):
        app = self.make_app()

        evidence = Evidence(
            source="runtime",
            detail="health inspection",
            content="runtime ready",
        )

        app.provider_registry = FakeRegistry(
            AnswerContext(
                evidence=(evidence,)
            )
        )

        client = FakeClient()
        app.runtime_manager = (
            FakeRuntimeManager(
                client=client
            )
        )

        owner_prompt = (
            "Tell me the current runtime state."
        )

        app._resolve_ask_answer(
            owner_prompt,
            [],
            "system",
        )

        messages = client.calls[0][0]

        self.assertGreaterEqual(
            len(messages),
            2,
        )

        self.assertEqual(
            messages[-1],
            {
                "role": "user",
                "content": owner_prompt,
            },
        )

        reference_messages = [
            message
            for message in messages[:-1]
            if (
                "REFERENCE EVIDENCE"
                in message["content"]
            )
        ]

        self.assertEqual(
            len(reference_messages),
            1,
        )

        reference = (
            reference_messages[0]["content"]
        )

        self.assertIn(
            "runtime ready",
            reference,
        )

        self.assertIn(
            "health inspection",
            reference,
        )

        self.assertNotEqual(
            reference,
            owner_prompt,
        )

    def test_knowledge_gap_is_structured_and_bypasses_model(self):
        app = self.make_app()

        gap = KnowledgeGap(
            unknown="active runtime model",
            missing_evidence=(
                "runtime health response",
                "reported model identity",
            ),
            reason=(
                "runtime inspection unavailable"
            ),
            resolution=(
                "start the runtime",
                "retry inspection",
            ),
        )

        app.provider_registry = FakeRegistry(
            AnswerContext(
                gap=gap
            )
        )

        app.runtime_manager = (
            ForbiddenRuntimeManager()
        )

        answer = app._resolve_ask_answer(
            "Which model is active?",
            [],
            "system",
        )

        self.assertIn(
            "active runtime model",
            answer,
        )
        self.assertIn(
            "runtime health response",
            answer,
        )
        self.assertIn(
            "reported model identity",
            answer,
        )
        self.assertIn(
            "runtime inspection unavailable",
            answer,
        )
        self.assertIn(
            "start the runtime",
            answer,
        )
        self.assertIn(
            "retry inspection",
            answer,
        )

    def test_runtime_readiness_happens_before_chat(self):
        app = self.make_app()

        app.provider_registry = FakeRegistry(
            AnswerContext()
        )

        events = []

        client = FakeClient(
            events=events
        )

        app.runtime_manager = (
            FakeRuntimeManager(
                client=client,
                events=events,
            )
        )

        app._resolve_ask_answer(
            "Count from one to three.",
            [],
            "general-chat",
        )

        self.assertEqual(
            events,
            [
                "ready_binding",
                "chat",
            ],
        )

    def test_previous_history_precedes_evidence_and_owner(self):
        app = self.make_app()

        evidence = Evidence(
            source="file",
            detail="local note",
            content="observed value",
        )

        app.provider_registry = FakeRegistry(
            AnswerContext(
                evidence=(evidence,)
            )
        )

        client = FakeClient()

        app.runtime_manager = (
            FakeRuntimeManager(
                client=client
            )
        )

        previous = [
            {
                "role": "assistant",
                "content": "earlier",
            }
        ]

        app._resolve_ask_answer(
            "current request",
            previous,
            "general-chat",
        )

        messages = client.calls[0][0]

        self.assertEqual(
            messages[0],
            previous[0],
        )

        self.assertEqual(
            messages[-1],
            {
                "role": "user",
                "content": "current request",
            },
        )


if __name__ == "__main__":
    unittest.main()
