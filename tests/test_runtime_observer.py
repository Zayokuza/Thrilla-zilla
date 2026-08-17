import importlib
import importlib.util
import unittest
from types import SimpleNamespace


class RuntimeProviderTests(unittest.TestCase):
    def provider_type(self):
        spec = importlib.util.find_spec(
            "thrilla.observers"
        )

        self.assertIsNotNone(spec)

        module = importlib.import_module(
            "thrilla.observers"
        )

        self.assertTrue(
            hasattr(module, "RuntimeProvider"),
            "RuntimeProvider is not implemented",
        )

        return module.RuntimeProvider

    @staticmethod
    def ready_snapshot():
        return SimpleNamespace(
            configured_endpoint=(
                "http://127.0.0.1:8080"
            ),
            expected_model="local-model",
            ready=True,
            detail=(
                "existing server is reusable"
            ),
            host="127.0.0.1",
            port=8080,
            ownership=None,
            reported_models=(
                "local-model",
            ),
            error="",
        )

    @staticmethod
    def failed_snapshot():
        return SimpleNamespace(
            configured_endpoint=(
                "http://127.0.0.1:8080"
            ),
            expected_model="local-model",
            ready=False,
            detail=(
                "connection refused"
            ),
            host="127.0.0.1",
            port=8080,
            ownership=None,
            reported_models=(),
            error=(
                "connection refused"
            ),
        )

    def provider(
        self,
        snapshot=None,
        calls=None,
    ):
        if snapshot is None:
            snapshot = self.ready_snapshot()

        if calls is None:
            calls = []

        def inspect_fn(
            model_url,
            expected_model,
        ):
            calls.append(
                (
                    model_url,
                    expected_model,
                )
            )
            return snapshot

        return self.provider_type()(
            inspect_fn=inspect_fn,
            model_url=(
                "http://127.0.0.1:8080"
            ),
            expected_model="local-model",
        )

    def test_recognizes_model_running_question(self):
        self.assertTrue(
            self.provider().supports(
                "Is my model running?"
            )
        )

    def test_recognizes_runtime_status_question(self):
        self.assertTrue(
            self.provider().supports(
                "What is the runtime status?"
            )
        )

    def test_recognizes_loaded_model_question(self):
        self.assertTrue(
            self.provider().supports(
                "What model is loaded?"
            )
        )

    def test_recognizes_llama_server_question(self):
        self.assertTrue(
            self.provider().supports(
                "Is llama-server alive?"
            )
        )

    def test_unrelated_prompt_is_unsupported(self):
        self.assertFalse(
            self.provider().supports(
                "Explain recursion."
            )
        )

    def test_runtime_inspection_receives_configuration(self):
        calls = []

        self.provider(
            calls=calls
        ).collect(
            "Is my model running?"
        )

        self.assertEqual(
            calls,
            [
                (
                    "http://127.0.0.1:8080",
                    "local-model",
                )
            ],
        )

    def test_ready_runtime_direct_answer(self):
        context = self.provider().collect(
            "Is my model running?"
        )

        self.assertIn(
            "Runtime ready: yes",
            context.direct_answer,
        )

        self.assertIn(
            "http://127.0.0.1:8080",
            context.direct_answer,
        )

        self.assertIn(
            "local-model",
            context.direct_answer,
        )

        self.assertIn(
            "127.0.0.1:8080",
            context.direct_answer,
        )

        self.assertIsNone(context.gap)

    def test_failed_runtime_direct_answer(self):
        context = self.provider(
            snapshot=self.failed_snapshot()
        ).collect(
            "Why can't you answer with the model?"
        )

        self.assertIn(
            "Runtime ready: no",
            context.direct_answer,
        )

        self.assertIn(
            "connection refused",
            context.direct_answer,
        )

        self.assertIsNone(context.gap)

    def test_runtime_evidence_is_structured(self):
        context = self.provider().collect(
            "What model is loaded?"
        )

        self.assertEqual(
            len(context.evidence),
            1,
        )

        evidence = context.evidence[0]

        self.assertEqual(
            evidence.source,
            "runtime_status",
        )

        self.assertIn(
            "runtime",
            evidence.detail.lower(),
        )

        self.assertIn(
            "Runtime ready: yes",
            evidence.content,
        )

    def test_direct_answer_allows_model_bypass(self):
        context = self.provider().collect(
            "Is the local AI ready?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )


if __name__ == "__main__":
    unittest.main()
