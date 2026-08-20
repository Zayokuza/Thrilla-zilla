import json
import tempfile
import unittest
from pathlib import Path

from thrilla.autonomy import AutonomousTaskRunner
from thrilla.tools import (
    ToolExecutor,
    ToolPermission,
    ToolRegistry,
    ToolSpec,
)


class ScriptedPlanner:
    def __init__(self, responses):
        self.responses = list(responses)

    def __call__(self, messages, route):
        if not self.responses:
            raise AssertionError("planner exhausted")
        return self.responses.pop(0)


def structured(source, detail):
    return {
        "source": source,
        "detail": detail,
    }


class Stage7EAutonomyBridgeTests(unittest.TestCase):
    def make_runner(self, responses):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        registry = ToolRegistry()

        registry.register(
            ToolSpec(
                "research.query",
                ToolPermission.NETWORK,
                "controlled research",
                lambda args: structured(
                    "research",
                    "research complete",
                ),
            )
        )

        registry.register(
            ToolSpec(
                "memory.remember",
                ToolPermission.WRITE,
                "controlled durable memory",
                lambda args: structured(
                    "memory",
                    "memory stored",
                ),
            )
        )

        registry.register(
            ToolSpec(
                "coding.repair",
                ToolPermission.WRITE,
                "checkpointed repair",
                lambda args: structured(
                    "coding",
                    "verified repair",
                ),
            )
        )

        registry.register(
            ToolSpec(
                "danger.write",
                ToolPermission.WRITE,
                "unrestricted write",
                lambda args: structured(
                    "danger",
                    "should never run",
                ),
            )
        )

        runner = AutonomousTaskRunner(
            tool_executor=ToolExecutor(registry),
            planner=ScriptedPlanner(responses),
            workspace=Path(temp.name),
            max_steps=8,
        )

        return runner

    def test_only_controlled_write_network_tools_enter_catalog(self):
        runner = self.make_runner(
            [
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "done",
                    }
                )
            ]
        )

        names = {
            item["name"]
            for item in runner.tool_catalog
        }

        self.assertIn(
            "research.query",
            names,
        )
        self.assertIn(
            "memory.remember",
            names,
        )
        self.assertIn(
            "coding.repair",
            names,
        )
        self.assertNotIn(
            "danger.write",
            names,
        )

    def test_runner_can_chain_research_and_memory(self):
        runner = self.make_runner(
            [
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "research.query",
                        "arguments": {
                            "query": "Thrilla",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "tool",
                        "tool": "memory.remember",
                        "arguments": {
                            "text": "Research completed.",
                        },
                    }
                ),
                json.dumps(
                    {
                        "action": "finish",
                        "answer": "Research completed and remembered.",
                    }
                ),
            ]
        )

        result = runner.run(
            "Research Thrilla and remember completion."
        )

        self.assertTrue(result.completed)
        self.assertEqual(result.tool_calls, 2)
        self.assertEqual(
            result.steps[0].tool,
            "research.query",
        )
        self.assertEqual(
            result.steps[1].tool,
            "memory.remember",
        )


if __name__ == "__main__":
    unittest.main()
