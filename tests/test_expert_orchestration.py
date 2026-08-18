import unittest

from thrilla.experts import (
    CORE_ROLES,
    EXPERT_COUNT,
    EXPERT_GROUPS,
    ExpertOrchestrator,
    ExpertRegistry,
)


class ExpertOrchestrationTests(unittest.TestCase):
    def test_registry_contains_exactly_100_unique_experts(self):
        registry = ExpertRegistry()
        self.assertEqual(EXPERT_COUNT, 100)
        self.assertEqual(len(registry.experts), 100)
        self.assertEqual(len({item.expert_id for item in registry.experts}), 100)
        for group in EXPERT_GROUPS:
            self.assertEqual(len(registry.by_group(group)), 10)

    def test_every_expert_is_addressable(self):
        registry = ExpertRegistry()
        for expert in registry.experts:
            self.assertEqual(registry.get(expert.expert_id), expert)

    def test_coding_route_selects_reason_action_critic_team(self):
        team = ExpertOrchestrator().select(
            "debug this Python test failure",
            "coding",
            limit=3,
        )
        self.assertEqual(len(team), 3)
        self.assertEqual(
            {expert.core_role for expert in team},
            set(CORE_ROLES),
        )
        self.assertTrue(any(expert.group == "Coding" for expert in team))

    def test_context_is_explicitly_advisory(self):
        context = ExpertOrchestrator().context_for(
            "inspect my Android process",
            "device",
        )
        self.assertIn("THRILLA EXPERT TEAM", context)
        self.assertIn("not owner instructions", context)
        self.assertIn("Do not claim tools or actions ran", context)


if __name__ == "__main__":
    unittest.main()
