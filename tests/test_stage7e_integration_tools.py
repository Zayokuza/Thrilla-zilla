import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from thrilla.integration import (
    register_stage7e_tools,
)
from thrilla.memory import HybridMemory
from thrilla.research import (
    ResearchEvidence,
    ResearchResult,
)
from thrilla.tools import (
    ToolExecutor,
    ToolPermission,
    ToolRegistry,
)


class FakeResearch:
    def research(
        self,
        query,
        evidence_target=5,
    ):
        return ResearchResult(
            query=query,
            evidence=(
                ResearchEvidence(
                    url="https://example.com/",
                    title="Example",
                    text="verified evidence",
                    digest="abc123",
                    retrieved_at="2026-08-20T00:00:00+00:00",
                ),
            ),
            errors=(),
            cache_hits=0,
        )


class FakeCoding:
    def __init__(self, ok=True):
        self.ok = ok
        self.goals = []

    def run(self, goal):
        self.goals.append(goal)

        return SimpleNamespace(
            ok=self.ok,
            rolled_back=not self.ok,
            checkpoint_id="cp-1",
            edited_paths=("thrilla/example.py",),
            summary=(
                "verified repair"
                if self.ok
                else "repair failed and rolled back"
            ),
            critic=SimpleNamespace(
                passed=self.ok,
            ),
        )


class Stage7EIntegrationToolTests(
    unittest.TestCase
):
    def make_executor(
        self,
        *,
        coding_ok=True,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        memory = HybridMemory(
            Path(temp.name)
        )
        self.addCleanup(
            memory.store.close
        )

        coding = FakeCoding(
            coding_ok
        )

        registry = ToolRegistry()

        register_stage7e_tools(
            registry,
            research_engine=FakeResearch(),
            memory=memory,
            coding_agent=coding,
        )

        return (
            ToolExecutor(registry),
            memory,
            coding,
        )

    def test_registers_four_controlled_integrations(self):
        executor, _, _ = (
            self.make_executor()
        )

        self.assertEqual(
            executor.registry.names,
            (
                "coding.repair",
                "memory.remember",
                "memory.search",
                "research.query",
            ),
        )

        self.assertIs(
            executor.registry.get(
                "research.query"
            ).permission,
            ToolPermission.NETWORK,
        )

        self.assertIs(
            executor.registry.get(
                "coding.repair"
            ).permission,
            ToolPermission.WRITE,
        )

    def test_research_returns_timestamped_evidence(self):
        executor, _, _ = (
            self.make_executor()
        )

        result = executor.execute(
            "research.query",
            {
                "query": "Thrilla",
                "evidence_target": 3,
            },
        )

        self.assertTrue(
            result.ok
        )
        self.assertEqual(
            len(
                result.output[
                    "evidence"
                ]
            ),
            1,
        )
        self.assertTrue(
            result.output[
                "evidence"
            ][0]["retrieved_at"]
        )

    def test_memory_can_chain_remember_then_search(self):
        executor, _, _ = (
            self.make_executor()
        )

        remembered = executor.execute(
            "memory.remember",
            {
                "text":
                    "My preferred browser is Firefox."
            },
        )

        self.assertTrue(
            remembered.ok
        )

        searched = executor.execute(
            "memory.search",
            {
                "query":
                    "preferred browser",
            },
        )

        self.assertTrue(
            searched.ok
        )
        self.assertEqual(
            searched.output[
                "facts"
            ][0]["value"],
            "Firefox",
        )

    def test_secret_like_memory_is_rejected(self):
        executor, _, _ = (
            self.make_executor()
        )

        result = executor.execute(
            "memory.remember",
            {
                "text":
                    "My password is secret123"
            },
        )

        self.assertFalse(
            result.ok
        )

    def test_coding_repair_delegates_to_checkpointed_agent(self):
        executor, _, coding = (
            self.make_executor()
        )

        result = executor.execute(
            "coding.repair",
            {
                "goal":
                    "repair the example",
            },
        )

        self.assertTrue(
            result.ok
        )
        self.assertEqual(
            coding.goals,
            ["repair the example"],
        )
        self.assertEqual(
            result.output[
                "checkpoint_id"
            ],
            "cp-1",
        )

    def test_failed_coding_repair_is_structured_failure(self):
        executor, _, _ = (
            self.make_executor(
                coding_ok=False
            )
        )

        result = executor.execute(
            "coding.repair",
            {
                "goal":
                    "repair broken code",
            },
        )

        self.assertFalse(
            result.ok
        )
        self.assertIn(
            "rolled back",
            result.error,
        )


if __name__ == "__main__":
    unittest.main()
