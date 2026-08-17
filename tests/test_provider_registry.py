import unittest

from thrilla.answers import (
    AnswerContext,
    Evidence,
)
from thrilla.providers import (
    EvidenceProvider,
    ProviderRegistry,
)


class FakeProvider(EvidenceProvider):
    def __init__(
        self,
        supported=True,
        context=None,
        error=None,
    ):
        self.supported = supported
        self.context = (
            context
            if context is not None
            else AnswerContext()
        )
        self.error = error
        self.support_calls = 0
        self.collect_calls = 0

    def supports(self, prompt):
        self.support_calls += 1
        return self.supported

    def collect(self, prompt):
        self.collect_calls += 1

        if self.error is not None:
            raise self.error

        return self.context


class ProviderRegistryTests(unittest.TestCase):
    def test_unsupported_provider_not_collected(self):
        provider = FakeProvider(
            supported=False
        )

        result = ProviderRegistry(
            [provider]
        ).collect("question")

        self.assertEqual(
            provider.support_calls,
            1,
        )
        self.assertEqual(
            provider.collect_calls,
            0,
        )
        self.assertEqual(
            result,
            AnswerContext(),
        )

    def test_supported_evidence_collected(self):
        evidence = Evidence(
            source="runtime",
            detail="health",
            content="ready",
        )

        result = ProviderRegistry(
            [
                FakeProvider(
                    context=AnswerContext(
                        evidence=(evidence,)
                    )
                )
            ]
        ).collect("status")

        self.assertEqual(
            result.evidence,
            (evidence,),
        )

    def test_direct_answer_stops_collection(self):
        first = FakeProvider(
            context=AnswerContext(
                direct_answer="answer"
            )
        )
        second = FakeProvider()

        result = ProviderRegistry(
            [first, second]
        ).collect("question")

        self.assertEqual(
            result.direct_answer,
            "answer",
        )
        self.assertEqual(
            second.support_calls,
            0,
        )
        self.assertEqual(
            second.collect_calls,
            0,
        )

    def test_evidence_order_is_deterministic(self):
        first = Evidence(
            source="one",
            detail="first",
            content="A",
        )
        second = Evidence(
            source="two",
            detail="second",
            content="B",
        )

        result = ProviderRegistry(
            [
                FakeProvider(
                    context=AnswerContext(
                        evidence=(first,)
                    )
                ),
                FakeProvider(
                    context=AnswerContext(
                        evidence=(second,)
                    )
                ),
            ]
        ).collect("question")

        self.assertEqual(
            result.evidence,
            (first, second),
        )

    def test_provider_failure_becomes_gap(self):
        result = ProviderRegistry(
            [
                FakeProvider(
                    error=RuntimeError(
                        "observer failed"
                    )
                )
            ]
        ).collect("question")

        self.assertIsNotNone(
            result.gap
        )
        self.assertIn(
            "observer failed",
            result.gap.reason,
        )
        self.assertTrue(
            result.gap.missing_evidence
        )
        self.assertTrue(
            result.gap.resolution
        )

    def test_prior_evidence_survives_later_failure(self):
        evidence = Evidence(
            source="one",
            detail="known",
            content="value",
        )

        result = ProviderRegistry(
            [
                FakeProvider(
                    context=AnswerContext(
                        evidence=(evidence,)
                    )
                ),
                FakeProvider(
                    error=OSError(
                        "later failed"
                    )
                ),
            ]
        ).collect("question")

        self.assertEqual(
            result.evidence,
            (evidence,),
        )
        self.assertIsNotNone(
            result.gap
        )

    def test_support_failure_becomes_gap(self):
        class BrokenProvider(
            EvidenceProvider
        ):
            def supports(self, prompt):
                raise RuntimeError(
                    "support failed"
                )

            def collect(self, prompt):
                raise AssertionError(
                    "must not collect"
                )

        result = ProviderRegistry(
            [BrokenProvider()]
        ).collect("question")

        self.assertIsNotNone(
            result.gap
        )
        self.assertIn(
            "support failed",
            result.gap.reason,
        )


if __name__ == "__main__":
    unittest.main()
