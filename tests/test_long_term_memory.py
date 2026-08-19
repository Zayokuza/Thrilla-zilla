import tempfile
import unittest
from pathlib import Path

from thrilla.memory import (
    HybridMemory,
    MemoryRejected,
    MemoryStore,
)


class DurableHybridMemoryTests(unittest.TestCase):
    def make_memory(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return HybridMemory(Path(temp.name))

    def test_automatic_high_confidence_facts_are_promoted(self):
        memory = self.make_memory()

        facts = memory.observe(
            "My name is Jesse and my favorite color is blue."
        )

        self.assertGreaterEqual(len(facts), 2)
        self.assertEqual(
            memory.store.fact_for(
                "owner",
                "name",
            ).value,
            "Jesse",
        )
        self.assertEqual(
            memory.store.fact_for(
                "owner",
                "favorite_color",
            ).value,
            "blue",
        )

    def test_new_value_supersedes_old_active_fact(self):
        memory = self.make_memory()

        first = memory.remember_explicit(
            "My preferred model is Gemma"
        )
        second = memory.remember_explicit(
            "My preferred model is Qwen"
        )

        self.assertNotEqual(
            first.fact_id,
            second.fact_id,
        )
        self.assertEqual(
            second.supersedes_id,
            first.fact_id,
        )
        self.assertEqual(
            memory.store.fact_for(
                "owner",
                "preferred_model",
            ).value,
            "Qwen",
        )
        self.assertEqual(
            len(
                [
                    fact
                    for fact in memory.store.active()
                    if fact.predicate == "preferred_model"
                ]
            ),
            1,
        )

    def test_secret_like_content_is_never_persisted(self):
        memory = self.make_memory()

        self.assertEqual(
            memory.observe(
                "My API key is sk-this-is-not-for-memory-123456"
            ),
            (),
        )

        with self.assertRaises(MemoryRejected):
            memory.remember_explicit(
                "My password is swordfish"
            )

        self.assertEqual(
            memory.store.count(),
            0,
        )

    def test_correction_and_forgetting_are_persistent(self):
        memory = self.make_memory()

        memory.remember_explicit(
            "My favorite editor is nano"
        )

        corrected = memory.correct(
            "favorite editor",
            "vim",
        )

        self.assertEqual(
            corrected.value,
            "vim",
        )

        forgotten = memory.forget(
            "favorite editor"
        )

        self.assertEqual(forgotten, 1)
        self.assertIsNone(
            memory.store.fact_for(
                "owner",
                "favorite_editor",
            )
        )

    def test_store_reuses_one_sqlite_connection(self):
        with tempfile.TemporaryDirectory() as root:
            store = MemoryStore(Path(root))
            first = store.connection_identity
            second = store.connection_identity

            self.assertEqual(first, second)


    def test_chained_owner_facts_stop_at_clause_boundaries(self):
        memory = self.make_memory()

        facts = memory.observe(
            "My name is Jesse and my favorite color is blue "
            "and my phone is Samsung S24 Ultra."
        )

        self.assertGreaterEqual(len(facts), 3)
        self.assertEqual(
            memory.store.fact_for("owner", "name").value,
            "Jesse",
        )
        self.assertEqual(
            memory.store.fact_for("owner", "favorite_color").value,
            "blue",
        )
        self.assertEqual(
            memory.store.fact_for("owner", "device_phone").value,
            "Samsung S24 Ultra",
        )


if __name__ == "__main__":
    unittest.main()
