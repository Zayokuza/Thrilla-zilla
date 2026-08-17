import inspect
import unittest
from types import SimpleNamespace

from thrilla import __version__
from thrilla.app import ThrillaApp


class FakeRuntimeManager:
    def __init__(self):
        self.calls = []

    def inspect_configured_runtime(
        self,
        model_url,
        expected_model,
    ):
        self.calls.append(
            (
                model_url,
                expected_model,
            )
        )

        return SimpleNamespace(
            configured_endpoint=model_url,
            expected_model=expected_model,
            ready=True,
            detail="test runtime is reusable",
            host="127.0.0.1",
            port=8080,
            ownership=None,
            reported_models=(
                expected_model,
            ),
            error="",
        )


class ObserverWiringTests(unittest.TestCase):
    def app_shell(self):
        app = ThrillaApp.__new__(
            ThrillaApp
        )

        app.config = SimpleNamespace(
            model_url=(
                "http://127.0.0.1:8080"
                "/v1/chat/completions"
            ),
            model_name="local-model",
        )

        app.runtime_manager = (
            FakeRuntimeManager()
        )

        def history_records(limit=None):
            records = [
                {
                    "timestamp": (
                        "2026-08-15T10:00:00+00:00"
                    ),
                    "role": "user",
                    "content": (
                        "The launch code name is "
                        "Thunder Road."
                    ),
                    "route": "general-chat",
                },
                {
                    "timestamp": (
                        "2026-08-15T10:01:00+00:00"
                    ),
                    "role": "assistant",
                    "content": (
                        "Thunder Road is recorded as "
                        "the launch code name."
                    ),
                    "route": "general-chat",
                },
            ]

            if limit is None:
                return list(records)

            bounded = max(0, int(limit))

            if bounded == 0:
                return []

            return list(records[-bounded:])

        app.history = SimpleNamespace(
            records=history_records,
        )

        return app

    def registry(self):
        app = self.app_shell()

        self.assertTrue(
            hasattr(
                app,
                "_provider_registry",
            ),
            (
                "ThrillaApp._provider_registry "
                "is not implemented"
            ),
        )

        return (
            app,
            app._provider_registry(),
        )

    def test_clock_provider_is_wired(self):
        app, registry = self.registry()
        del app

        context = registry.collect(
            "What time is it?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "Local time:",
            context.direct_answer,
        )

        self.assertEqual(
            context.evidence[0].source,
            "system_clock",
        )

    def test_runtime_provider_is_wired(self):
        app, registry = self.registry()

        context = registry.collect(
            "Is my model running?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "Runtime ready: yes",
            context.direct_answer,
        )

        self.assertIn(
            app.config.model_url,
            context.direct_answer,
        )

        self.assertIn(
            app.config.model_name,
            context.direct_answer,
        )

        self.assertEqual(
            app.runtime_manager.calls,
            [
                (
                    app.config.model_url,
                    app.config.model_name,
                )
            ],
        )

        self.assertEqual(
            context.evidence[0].source,
            "runtime_status",
        )

    def test_self_provider_is_wired(self):
        app, registry = self.registry()
        del app

        context = registry.collect(
            "What version are you?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "Project: THRILLA-ZILLA",
            context.direct_answer,
        )

        self.assertIn(
            "Version: {0}".format(
                __version__
            ),
            context.direct_answer,
        )

        self.assertIn(
            "Repository root:",
            context.direct_answer,
        )

        self.assertIn(
            "Branch:",
            context.direct_answer,
        )

        self.assertIn(
            "HEAD:",
            context.direct_answer,
        )

        self.assertEqual(
            context.evidence[0].source,
            "repository_state",
        )

    def test_memory_provider_is_wired(self):
        app, registry = self.registry()
        del app

        context = registry.collect(
            "What did I say about the launch code?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )

        self.assertIn(
            "Thunder Road",
            context.direct_answer,
        )

        self.assertEqual(
            len(context.evidence),
            1,
        )

        self.assertEqual(
            context.evidence[0].source,
            "local_conversation_history",
        )

    def test_unrelated_prompt_falls_through(self):
        app, registry = self.registry()
        del app

        context = registry.collect(
            "Explain recursion."
        )

        self.assertIsNone(
            context.direct_answer
        )

        self.assertIsNone(
            context.gap
        )

        self.assertEqual(
            context.evidence,
            (),
        )

    def test_constructor_uses_real_provider_registry(self):
        source = inspect.getsource(
            ThrillaApp.__init__
        )

        self.assertIn(
            (
                "self.provider_registry = "
                "self._provider_registry()"
            ),
            source,
        )

        self.assertNotIn(
            "ProviderRegistry(())",
            source,
        )

    def test_refresh_rebuilds_provider_registry(self):
        source = inspect.getsource(
            ThrillaApp._refresh
        )

        self.assertIn(
            (
                "self.provider_registry = "
                "self._provider_registry()"
            ),
            source,
        )

    def test_runtime_configuration_is_not_hardcoded(self):
        app, registry = self.registry()

        app.config.model_url = (
            "http://127.0.0.1:9191"
            "/v1/chat/completions"
        )
        app.config.model_name = (
            "changed-test-model"
        )

        registry = (
            app._provider_registry()
        )

        context = registry.collect(
            "What is the runtime status?"
        )

        self.assertIn(
            (
                "http://127.0.0.1:9191"
                "/v1/chat/completions"
            ),
            context.direct_answer,
        )

        self.assertIn(
            "changed-test-model",
            context.direct_answer,
        )

    def test_provider_direct_answer_preserves_model_bypass(self):
        app, registry = self.registry()
        app.provider_registry = registry

        def fail_ready_binding(
            *args,
            **kwargs
        ):
            raise AssertionError(
                (
                    "model runtime must not be "
                    "used for direct provider "
                    "answers"
                )
            )

        app.runtime_manager.ready_binding = (
            fail_ready_binding
        )

        answer = app._resolve_ask_answer(
            "What version are you?",
            [],
            "chat",
        )

        self.assertIn(
            "Project: THRILLA-ZILLA",
            answer,
        )


if __name__ == "__main__":
    unittest.main()
