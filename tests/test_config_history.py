import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from thrilla.config import Config
from thrilla.history import ConversationHistory


class ConfigHistoryTests(unittest.TestCase):
    def test_config_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            config = Config.defaults()
            config.color_mode = "always"
            config.model_name = "test-model"
            config.save(path)
            loaded = Config.load(path)
            self.assertEqual("always", loaded.color_mode)
            self.assertEqual("test-model", loaded.model_name)

    def test_environment_state_root_wins_over_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(json.dumps({"state_root": "/stale", "request_timeout": "bad"}), encoding="utf-8")
            wanted = str(Path(temporary) / "state")
            with patch.dict(os.environ, {"THRILLA_HOME": wanted}):
                loaded = Config.load(path)
            self.assertEqual(wanted, loaded.state_root)
            self.assertEqual(90.0, loaded.request_timeout)

    def test_history_context_is_bounded_and_clear_preserves_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            history = ConversationHistory(Path(temporary))
            for index in range(4):
                history.append("user", f"question {index}", "general-chat")
                history.append("assistant", f"answer {index}", "general-chat")
            self.assertEqual(4, len(history.messages(turns=2)))
            self.assertTrue(history.clear())
            self.assertEqual([], history.records())
            self.assertTrue((Path(temporary) / "conversation.cleared.jsonl").exists())

    def test_zero_history_limit_returns_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            history = ConversationHistory(Path(temporary))
            history.append("user", "private text")
            self.assertEqual([], history.records(limit=0))


if __name__ == "__main__":
    unittest.main()
