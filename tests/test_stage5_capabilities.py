"""Stage 5 final capability/release contract."""

import unittest

import thrilla.capabilities as capabilities


class Stage5CapabilityTests(unittest.TestCase):
    def test_stage_is_five(self):
        self.assertEqual(capabilities.STAGE, 5)

    def test_stage5_live_features_are_active(self):
        joined = "\n".join(capabilities.ACTIVE_CAPABILITIES).lower()
        for required in (
            "background",
            "research",
            "communicat",
            "hold",
            "cache",
        ):
            with self.subTest(required=required):
                self.assertIn(required, joined)

    def test_only_stage6_acceptance_remains_future(self):
        joined = "\n".join(capabilities.FUTURE_CAPABILITIES).lower()
        self.assertIn("release-candidate", joined)
        self.assertNotIn("web research", joined)
        self.assertNotIn("multi-step workflows", joined)

    def test_v1_release_still_requires_owner_authorization(self):
        policy = capabilities.RELEASE_POLICY.lower()
        self.assertIn("not v1.0.0", policy)
        self.assertIn("owner explicitly authorizes", policy)


if __name__ == "__main__":
    unittest.main()
