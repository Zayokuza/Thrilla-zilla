import importlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from thrilla.app import ThrillaApp
from thrilla.config import Config


EXPECTED_GROUPS = (
    "Agent Brain",
    "Coding",
    "AI Runtime",
    "Build / Language",
    "Memory / State",
    "Web Research",
    "Tools / Flows",
    "Execution / OS",
    "Interface / API",
    "Evaluation / Security",
)


class ExpertInvariantTests(unittest.TestCase):
    def load_experts(self):
        spec = importlib.util.find_spec(
            "thrilla.experts"
        )

        self.assertIsNotNone(
            spec,
            "thrilla.experts does not exist yet",
        )

        return importlib.import_module(
            "thrilla.experts"
        )

    def test_exactly_ten_expert_groups_exist(self):
        experts = self.load_experts()

        self.assertEqual(
            experts.EXPERT_GROUPS,
            EXPECTED_GROUPS,
        )

        self.assertEqual(
            len(experts.EXPERT_GROUPS),
            10,
        )

    def test_each_group_represents_ten_experts(self):
        experts = self.load_experts()

        self.assertEqual(
            experts.EXPERTS_PER_GROUP,
            10,
        )

    def test_total_expert_count_is_exactly_100(self):
        experts = self.load_experts()

        self.assertEqual(
            experts.EXPERT_COUNT,
            100,
        )

        self.assertEqual(
            len(experts.EXPERT_GROUPS)
            * experts.EXPERTS_PER_GROUP,
            100,
        )

    def test_expert_count_is_never_98(self):
        experts = self.load_experts()

        self.assertNotEqual(
            experts.EXPERT_COUNT,
            98,
        )

    def test_about_distinguishes_experts_from_donors(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        config = Config.defaults()
        config.state_root = str(
            Path(temp.name) / "state"
        )
        config.donor_root = str(
            Path(temp.name) / "donors"
        )
        config.color_mode = "never"

        app = ThrillaApp(config)

        app._header = Mock()
        app._pause = Mock()

        with patch(
            "builtins.print"
        ) as output:
            app.about()

        rendered = "\n".join(
            str(call.args[0])
            for call in output.call_args_list
            if call.args
        )

        normalized = " ".join(
            rendered.lower().split()
        )

        self.assertIn(
            "100 experts",
            normalized,
        )

        self.assertIn(
            "100 donor repositories",
            normalized,
        )

        self.assertIn(
            "separate",
            normalized,
        )

        self.assertIn(
            "expert orchestration is active",
            normalized,
        )

        self.assertNotIn(
            "98 experts",
            normalized,
        )


if __name__ == "__main__":
    unittest.main()
