import unittest
from dataclasses import FrozenInstanceError

from thrilla.answers import (
    AnswerContext,
    Evidence,
    KnowledgeGap,
)


class EvidenceTests(unittest.TestCase):
    def test_evidence_preserves_fields(self):
        item = Evidence(
            source="runtime",
            detail="configured endpoint",
            content="ready",
        )

        self.assertEqual(item.source, "runtime")
        self.assertEqual(
            item.detail,
            "configured endpoint",
        )
        self.assertEqual(item.content, "ready")

    def test_evidence_is_immutable(self):
        item = Evidence(
            source="source",
            detail="file",
            content="value",
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            item.content = "changed"


class KnowledgeGapTests(unittest.TestCase):
    def test_gap_is_structured(self):
        gap = KnowledgeGap(
            unknown="active model",
            missing_evidence=(
                "runtime response",
                "reported model",
            ),
            reason="runtime unavailable",
            resolution=(
                "start runtime",
                "retry inspection",
            ),
        )

        self.assertEqual(
            gap.unknown,
            "active model",
        )
        self.assertEqual(
            gap.missing_evidence,
            (
                "runtime response",
                "reported model",
            ),
        )
        self.assertEqual(
            gap.reason,
            "runtime unavailable",
        )
        self.assertEqual(
            gap.resolution,
            (
                "start runtime",
                "retry inspection",
            ),
        )

    def test_gap_is_immutable(self):
        gap = KnowledgeGap(
            unknown="state",
            missing_evidence=("evidence",),
            reason="missing",
            resolution=("inspect",),
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            gap.reason = "changed"


class AnswerContextTests(unittest.TestCase):
    def test_defaults_are_empty_and_immutable(self):
        context = AnswerContext()

        self.assertIsNone(
            context.direct_answer
        )
        self.assertEqual(
            context.evidence,
            (),
        )
        self.assertIsNone(context.gap)

        with self.assertRaises(
            FrozenInstanceError
        ):
            context.direct_answer = "changed"

    def test_supports_direct_answer(self):
        context = AnswerContext(
            direct_answer="Observed."
        )

        self.assertEqual(
            context.direct_answer,
            "Observed.",
        )

    def test_supports_evidence(self):
        item = Evidence(
            source="clock",
            detail="local clock",
            content="04:03",
        )

        context = AnswerContext(
            evidence=(item,)
        )

        self.assertEqual(
            context.evidence,
            (item,),
        )

    def test_supports_gap(self):
        gap = KnowledgeGap(
            unknown="temperature",
            missing_evidence=("sensor",),
            reason="unavailable",
            resolution=("attach sensor",),
        )

        context = AnswerContext(gap=gap)

        self.assertIs(
            context.gap,
            gap,
        )


if __name__ == "__main__":
    unittest.main()
