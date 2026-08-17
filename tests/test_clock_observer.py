import importlib
import importlib.util
import unittest
from datetime import (
    datetime,
    timedelta,
    timezone,
)


FIXED = datetime(
    2026,
    8,
    17,
    11,
    13,
    42,
    tzinfo=timezone(
        timedelta(hours=-5)
    ),
)


class ClockProviderTests(unittest.TestCase):
    def provider_type(self):
        spec = importlib.util.find_spec(
            "thrilla.observers"
        )

        self.assertIsNotNone(
            spec,
            "thrilla.observers is not implemented",
        )

        module = importlib.import_module(
            "thrilla.observers"
        )

        self.assertTrue(
            hasattr(module, "ClockProvider"),
            "ClockProvider is not implemented",
        )

        return module.ClockProvider

    def provider(self):
        return self.provider_type()(
            now_fn=lambda: FIXED
        )

    def test_recognizes_current_time_question(self):
        self.assertTrue(
            self.provider().supports(
                "What time is it?"
            )
        )

    def test_recognizes_current_date_question(self):
        self.assertTrue(
            self.provider().supports(
                "What is today's date?"
            )
        )

    def test_recognizes_current_day_question(self):
        self.assertTrue(
            self.provider().supports(
                "What day is it?"
            )
        )

    def test_unrelated_prompt_is_unsupported(self):
        self.assertFalse(
            self.provider().supports(
                "Explain how recursion works."
            )
        )

    def test_fixed_offset_aware_datetime_is_returned_exactly(self):
        context = self.provider().collect(
            "What time and date is it?"
        )

        self.assertEqual(
            context.direct_answer,
            (
                "Local date: 2026-08-17\n"
                "Local time: 11:13:42\n"
                "Day: Monday\n"
                "UTC offset: -05:00"
            ),
        )

        self.assertIsNone(context.gap)

    def test_evidence_comes_from_system_clock(self):
        context = self.provider().collect(
            "What time is it?"
        )

        self.assertEqual(
            len(context.evidence),
            1,
        )

        evidence = context.evidence[0]

        self.assertEqual(
            evidence.source,
            "system_clock",
        )

        self.assertIn(
            "local system clock",
            evidence.detail.lower(),
        )

        self.assertIn(
            "2026-08-17",
            evidence.content,
        )

        self.assertIn(
            "11:13:42",
            evidence.content,
        )

        self.assertIn(
            "-05:00",
            evidence.content,
        )

    def test_direct_answer_allows_model_bypass(self):
        context = self.provider().collect(
            "What time is it?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )


if __name__ == "__main__":
    unittest.main()
