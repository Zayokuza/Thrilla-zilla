import unittest

from thrilla.capabilities import (
    ACTIVE_CAPABILITIES,
    FUTURE_CAPABILITIES,
    STAGE,
    self_description,
)


class Stage7ECapabilityTruthTests(unittest.TestCase):
    def test_stage_truth_is_stage7(self):
        self.assertEqual(STAGE, 7)

        description = self_description("Owner")

        self.assertIn(
            "Roadmap stage: 7",
            description,
        )

        self.assertIn(
            "7F final acceptance open",
            description,
        )

    def test_active_truth_describes_autonomous_integration(self):
        text = "\n".join(
            ACTIVE_CAPABILITIES
        ).lower()

        self.assertIn(
            "multi-step autonomous",
            text,
        )

        self.assertIn(
            "research",
            text,
        )

        self.assertIn(
            "durable memory",
            text,
        )

        self.assertIn(
            "checkpointed coding",
            text,
        )

        future = "\n".join(
            FUTURE_CAPABILITIES
        ).lower()

        self.assertIn(
            "7f",
            future,
        )


if __name__ == "__main__":
    unittest.main()
