import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from thrilla.model import ModelError
from thrilla.runtime.supervisor import RuntimeSupervisor


class CountingReader:
    def __init__(self):
        self.calls = 0

    def __call__(self, path):
        self.calls += 1
        return path.read_text(encoding="utf-8", errors="replace")


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def chat(self, messages, route):
        del messages, route
        self.calls += 1
        if self.fail:
            raise ModelError("simulated model failure")
        return "ok"


class FakeManager:
    def __init__(self, client=None):
        self.calls = 0
        self.client = client or FakeClient()

    def ready_binding(self, model_url, model_name):
        del model_url, model_name
        self.calls += 1
        return SimpleNamespace(client=self.client)


def fake_config():
    return SimpleNamespace(
        model_url="http://127.0.0.1:8080/v1/chat/completions",
        model_name="local-model",
        runtime_autostart=False,
    )


class Stage7APerformanceTests(unittest.TestCase):
    def test_repository_index_module_exists(self):
        self.assertIsNotNone(
            importlib.util.find_spec("thrilla.performance"),
            "Stage 7A requires the repository performance index",
        )

    def test_repository_index_reuses_unchanged_file_content(self):
        from thrilla.performance import RepositoryIndex

        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            source = repo / "thrilla"
            source.mkdir()
            target = source / "sample.py"
            target.write_text(
                "alpha beta gamma\n",
                encoding="utf-8",
            )

            reader = CountingReader()
            index = RepositoryIndex(
                repo,
                search_roots=("thrilla",),
                supported_suffixes={".py"},
                reader=reader,
            )

            first = index.rank(("alpha",), max_files=3)
            second = index.rank(("alpha",), max_files=3)

            self.assertEqual(first, ("thrilla/sample.py",))
            self.assertEqual(second, first)
            self.assertEqual(
                reader.calls,
                1,
                "unchanged source must not be reread",
            )

            target.write_text(
                "alpha beta gamma delta epsilon\n",
                encoding="utf-8",
            )

            third = index.rank(("epsilon",), max_files=3)

            self.assertEqual(third, ("thrilla/sample.py",))
            self.assertEqual(
                reader.calls,
                2,
                "changed source must invalidate its cached content",
            )

    def test_runtime_binding_is_reused_between_successful_chats(self):
        manager = FakeManager()
        supervisor = RuntimeSupervisor(
            fake_config(),
            manager,
        )

        self.assertEqual(
            supervisor.chat([], "general-chat"),
            "ok",
        )
        self.assertEqual(
            supervisor.chat([], "general-chat"),
            "ok",
        )

        self.assertEqual(manager.calls, 1)
        self.assertEqual(manager.client.calls, 2)

    def test_replacing_runtime_manager_invalidates_binding_cache(self):
        first = FakeManager()
        second = FakeManager()

        supervisor = RuntimeSupervisor(
            fake_config(),
            first,
        )

        self.assertEqual(
            supervisor.chat([], "general-chat"),
            "ok",
        )

        supervisor.manager = second

        self.assertEqual(
            supervisor.chat([], "general-chat"),
            "ok",
        )

        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)

    def test_model_failure_invalidates_binding_cache(self):
        client = FakeClient()
        manager = FakeManager(client)
        supervisor = RuntimeSupervisor(
            fake_config(),
            manager,
        )

        client.fail = True

        with self.assertRaises(ModelError):
            supervisor.chat([], "general-chat")

        self.assertEqual(manager.calls, 1)

        client.fail = False

        self.assertEqual(
            supervisor.chat([], "general-chat"),
            "ok",
        )

        self.assertEqual(
            manager.calls,
            2,
            "a failed model request must force fresh readiness proof",
        )


if __name__ == "__main__":
    unittest.main()
