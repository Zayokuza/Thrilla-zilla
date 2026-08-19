import unittest

from thrilla.config import Config
from thrilla.model import LocalModelClient
from thrilla.runtime.manager import RuntimeManager
from thrilla.runtime.supervisor import RuntimeSupervisor


class ModelLatencyGuardTests(unittest.TestCase):
    def test_general_chat_keeps_only_bounded_recent_history(self):
        messages = []
        for index in range(6):
            messages.extend(
                (
                    {
                        "role": "user",
                        "content": "u{0} ".format(index) + ("x" * 100),
                    },
                    {
                        "role": "assistant",
                        "content": "a{0} ".format(index) + ("y" * 100),
                    },
                )
            )
        messages.append(
            {
                "role": "user",
                "content": "current",
            }
        )

        sent = LocalModelClient._normalize_messages(
            messages,
            "general-chat",
        )

        roles = [item["role"] for item in sent]
        self.assertEqual(
            roles,
            ["system", "user", "assistant", "user", "assistant", "user"],
        )
        self.assertIn("u4 ", sent[1]["content"])
        self.assertIn("a4 ", sent[2]["content"])
        self.assertIn("u5 ", sent[3]["content"])
        self.assertIn("a5 ", sent[4]["content"])
        self.assertEqual(sent[5]["content"], "current")

    def test_general_chat_drops_one_oversized_history_pair(self):
        messages = [
            {"role": "user", "content": "x" * 1200},
            {"role": "assistant", "content": "y" * 1200},
            {"role": "user", "content": "hey"},
        ]

        sent = LocalModelClient._normalize_messages(
            messages,
            "general-chat",
        )

        self.assertEqual(
            [item["role"] for item in sent],
            ["system", "user"],
        )
        self.assertEqual(sent[-1]["content"], "hey")

    def test_new_install_timeout_is_long_enough_for_heavy_local_prompt(self):
        self.assertGreaterEqual(
            Config.defaults().request_timeout,
            180.0,
        )

    def test_managed_runtime_enables_prompt_cache(self):
        config = Config.defaults()
        manager = RuntimeManager.from_config(config)
        supervisor = RuntimeSupervisor(config, manager)

        command = supervisor._command(
            "llama-server",
            Config.defaults().state_path / "model.gguf",
            "127.0.0.1",
            8080,
        )

        index = command.index("--cache-ram")
        self.assertGreater(
            int(command[index + 1]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
