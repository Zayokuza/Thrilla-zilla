import json
import tempfile
import unittest
from pathlib import Path

from thrilla.history import ConversationHistory


class ConversationHistoryCacheTests(unittest.TestCase):
    def test_append_updates_loaded_cache_without_reloading_file(self):
        with tempfile.TemporaryDirectory() as root:
            history = ConversationHistory(Path(root))

            self.assertEqual(
                history.records(),
                [],
            )
            cache = history._cache

            history.append(
                "user",
                "hello",
                "general-chat",
            )

            self.assertIs(
                history._cache,
                cache,
            )
            self.assertEqual(
                history.records()[0]["content"],
                "hello",
            )

    def test_reload_picks_up_external_changes_when_requested(self):
        with tempfile.TemporaryDirectory() as root:
            history = ConversationHistory(Path(root))
            history.append(
                "user",
                "first",
            )
            history.records()

            with history.path.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    json.dumps(
                        {
                            "role": "assistant",
                            "content": "external",
                        }
                    )
                    + "\n"
                )

            self.assertEqual(
                len(history.records()),
                1,
            )

            history.reload()

            self.assertEqual(
                len(history.records()),
                2,
            )

    def test_clear_resets_cache(self):
        with tempfile.TemporaryDirectory() as root:
            history = ConversationHistory(Path(root))
            history.append(
                "user",
                "hello",
            )
            history.records()

            self.assertTrue(
                history.clear()
            )
            self.assertEqual(
                history.records(),
                [],
            )


if __name__ == "__main__":
    unittest.main()
