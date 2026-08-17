import importlib
import importlib.util
import unittest


class MemoryProviderTests(unittest.TestCase):
    def provider_type(self):
        spec = importlib.util.find_spec(
            "thrilla.observers"
        )

        self.assertIsNotNone(spec)

        module = importlib.import_module(
            "thrilla.observers"
        )

        self.assertTrue(
            hasattr(module, "MemoryProvider"),
            "MemoryProvider is not implemented",
        )

        return module.MemoryProvider

    def provider(
        self,
        records=None,
        calls=None,
    ):
        if records is None:
            records = [
                {
                    "timestamp": "2026-08-15T10:00:00+00:00",
                    "role": "user",
                    "content": (
                        "The launch code name is Thunder Road."
                    ),
                    "route": "general-chat",
                },
                {
                    "timestamp": "2026-08-15T10:01:00+00:00",
                    "role": "assistant",
                    "content": (
                        "I recorded Thunder Road as the "
                        "launch code name."
                    ),
                    "route": "general-chat",
                },
                {
                    "timestamp": "2026-08-16T09:00:00+00:00",
                    "role": "user",
                    "content": (
                        "The truck needs an oil change."
                    ),
                    "route": "general-chat",
                },
            ]

        if calls is None:
            calls = []

        def records_fn(limit=None):
            calls.append(limit)

            if limit is None:
                return list(records)

            return list(records)[-limit:]

        return self.provider_type()(
            records_fn=records_fn,
            max_records=200,
            max_matches=6,
        )

    def test_recognizes_explicit_recall_question(self):
        self.assertTrue(
            self.provider().supports(
                "What did I say about the launch code?"
            )
        )

    def test_recognizes_remember_question(self):
        self.assertTrue(
            self.provider().supports(
                "Do you remember Thunder Road?"
            )
        )

    def test_recognizes_previous_discussion_question(self):
        self.assertTrue(
            self.provider().supports(
                "What did we talk about earlier?"
            )
        )

    def test_unrelated_prompt_is_unsupported(self):
        self.assertFalse(
            self.provider().supports(
                "Explain recursion."
            )
        )

    def test_reads_bounded_history(self):
        calls = []

        self.provider(
            calls=calls
        ).collect(
            "What did I say about the launch code?"
        )

        self.assertEqual(
            calls,
            [200],
        )

    def test_relevant_history_is_returned(self):
        context = self.provider().collect(
            "What did I say about the launch code?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "Thunder Road",
            context.direct_answer,
        )

        self.assertNotIn(
            "oil change",
            context.direct_answer,
        )

        self.assertIsNone(
            context.gap
        )

    def test_current_prompt_is_not_recalled_as_memory(self):
        prompt = (
            "What did I say about the launch code?"
        )

        records = [
            {
                "timestamp": "2026-08-15T10:00:00+00:00",
                "role": "user",
                "content": (
                    "The launch code name is Thunder Road."
                ),
            },
            {
                "timestamp": "2026-08-17T20:00:00+00:00",
                "role": "user",
                "content": prompt,
            },
        ]

        context = self.provider(
            records=records
        ).collect(prompt)

        self.assertIn(
            "Thunder Road",
            context.direct_answer,
        )

        self.assertEqual(
            context.direct_answer.count(prompt),
            0,
        )

    def test_generic_earlier_question_uses_recent_history(self):
        context = self.provider().collect(
            "What did we talk about earlier?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "oil change",
            context.direct_answer,
        )

    def test_missing_memory_becomes_structured_gap(self):
        context = self.provider().collect(
            "What did I say about quantum bananas?"
        )

        self.assertIsNone(
            context.direct_answer
        )

        self.assertIsNotNone(
            context.gap
        )

        self.assertIn(
            "conversation history",
            context.gap.reason.lower(),
        )

    def test_memory_evidence_is_structured(self):
        context = self.provider().collect(
            "Do you remember Thunder Road?"
        )

        self.assertEqual(
            len(context.evidence),
            1,
        )

        evidence = context.evidence[0]

        self.assertEqual(
            evidence.source,
            "local_conversation_history",
        )

        self.assertIn(
            "evidence only",
            evidence.detail.lower(),
        )

        self.assertIn(
            "Thunder Road",
            evidence.content,
        )

    def test_direct_answer_allows_model_bypass(self):
        context = self.provider().collect(
            "What did I say about the launch code?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )


if __name__ == "__main__":
    unittest.main()
