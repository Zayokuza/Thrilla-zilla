import gc
import tempfile
import unittest
import warnings
import weakref
from unittest.mock import Mock

from thrilla.app import ThrillaApp
from thrilla.config import Config
from thrilla.knowledge import SelfKnowledgeProvider


class StageOneToFiveHardeningTests(unittest.TestCase):
    def test_unclosed_app_gc_closes_memory_store(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = root
            config.donor_root = root
            config.owner_name = "Owner"

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)

                app = ThrillaApp(config)
                store = app.memory.store
                store.count()
                self.assertIsNotNone(store._connection)

                app_ref = weakref.ref(app)
                del app
                gc.collect()

                self.assertIsNone(app_ref())
                self.assertIsNone(
                    store._connection,
                    "dropping ThrillaApp must close its memory DB",
                )

            resource_warnings = [
                item
                for item in caught
                if issubclass(item.category, ResourceWarning)
            ]
            self.assertEqual(resource_warnings, [])

    def test_functioning_question_is_self_knowledge(self):
        provider = SelfKnowledgeProvider(
            owner_name_fn=lambda: "Owner",
        )

        self.assertTrue(
            provider.supports(
                "what is and isnt functioning"
            )
        )

        answer = provider.collect(
            "what is and isnt functioning"
        ).direct_answer

        self.assertIn("Roadmap stage: 5/6", answer)
        self.assertIn("Active capabilities:", answer)
        self.assertIn("Not active yet:", answer)

    def test_functioning_question_bypasses_model(self):
        with tempfile.TemporaryDirectory() as root:
            config = Config.defaults()
            config.state_root = root
            config.donor_root = root
            config.owner_name = "Owner"
            config.save_history = False

            app = ThrillaApp(config)
            self.addCleanup(app.close)

            app.runtime_supervisor.chat = Mock(
                side_effect=AssertionError(
                    "self-status must not use model inference"
                )
            )

            answer = app._resolve_ask_answer(
                "what is and isnt functioning",
                [],
                "general-chat",
            )

            self.assertIn("Roadmap stage: 5/6", answer)
            self.assertIn("Active capabilities:", answer)
            app.runtime_supervisor.chat.assert_not_called()

            lowered = answer.lower()
            self.assertNotIn("september 2021", lowered)
            self.assertNotIn("october 26, 2023", lowered)
            self.assertNotIn(
                "cannot currently execute external tools",
                lowered,
            )


if __name__ == "__main__":
    unittest.main()
