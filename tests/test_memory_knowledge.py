import tempfile
import unittest
from pathlib import Path

from thrilla.capabilities import RELEASE_POLICY
from thrilla.knowledge import (
    OwnerMemoryProvider,
    SelfKnowledgeProvider,
)
from thrilla.memory import HybridMemory


class KnowledgeProviderTests(unittest.TestCase):
    def test_owner_query_returns_direct_memory_answer(self):
        with tempfile.TemporaryDirectory() as root:
            memory = HybridMemory(Path(root))
            memory.remember_explicit(
                "My name is Jesse"
            )

            provider = OwnerMemoryProvider(
                memory,
                owner_name_fn=lambda: "",
            )

            self.assertTrue(
                provider.supports(
                    "what is my name"
                )
            )

            context = provider.collect(
                "what is my name"
            )

            self.assertEqual(
                context.direct_answer,
                "Your name is Jesse.",
            )
            self.assertEqual(
                context.evidence[0].source,
                "durable_owner_memory",
            )

    def test_self_knowledge_is_code_owned_and_release_policy_is_explicit(self):
        provider = SelfKnowledgeProvider(
            owner_name_fn=lambda: "Jesse"
        )

        context = provider.collect(
            "what can you do"
        )

        self.assertIn(
            "Name: Thrilla-zilla",
            context.direct_answer,
        )
        self.assertIn(
            "Owner: Jesse",
            context.direct_answer,
        )
        self.assertIn(
            "Roadmap stage: 5/6",
            context.direct_answer,
        )
        self.assertIn(
            RELEASE_POLICY,
            context.direct_answer,
        )


if __name__ == "__main__":
    unittest.main()
