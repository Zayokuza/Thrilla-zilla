import dataclasses
import importlib
import unittest
from unittest.mock import patch


class RuntimeStatusTests(unittest.TestCase):

    def _modules(self):
        try:
            status = importlib.import_module(
                "thrilla.runtime.status"
            )
        except Exception as error:
            self.fail(
                "runtime status module must exist: {0}".format(
                    error
                )
            )

        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        return status, manager, health

    def test_runtime_status_snapshot_is_immutable(self):
        status, _, _ = self._modules()

        snapshot = status.RuntimeStatusSnapshot(
            configured_endpoint=(
                "http://127.0.0.1:8080/v1/chat/completions"
            ),
            expected_model="thrilla-model",
            ready=True,
            detail="ready",
        )

        with self.assertRaises(
            dataclasses.FrozenInstanceError
        ):
            snapshot.ready = False

    def test_compatible_runtime_produces_ready_status(self):
        status, manager, health = self._modules()

        runtime = manager.RuntimeManager(
            health_timeout=0.75
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("thrilla-model",),
            expected_model="thrilla-model",
            model_match=True,
            reusable=True,
            detail="models endpoint responded",
        )

        endpoint = (
            "http://127.0.0.1:8080/v1/chat/completions"
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ):
            snapshot = (
                runtime.inspect_configured_runtime(
                    endpoint,
                    "thrilla-model",
                )
            )

        self.assertIsInstance(
            snapshot,
            status.RuntimeStatusSnapshot,
        )
        self.assertEqual(
            endpoint,
            snapshot.configured_endpoint,
        )
        self.assertEqual(
            "thrilla-model",
            snapshot.expected_model,
        )
        self.assertTrue(snapshot.ready)
        self.assertEqual(
            "127.0.0.1",
            snapshot.host,
        )
        self.assertEqual(
            8080,
            snapshot.port,
        )
        self.assertEqual(
            ("thrilla-model",),
            snapshot.reported_models,
        )
        self.assertIsNone(
            snapshot.ownership,
        )
        self.assertEqual(
            "",
            snapshot.error,
        )

    def test_unreachable_runtime_produces_truthful_failed_status(self):
        _, manager, health = self._modules()

        runtime = manager.RuntimeManager(
            health_timeout=0.5
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=False,
            bindable=True,
            openai_compatible=False,
            models=(),
            expected_model="thrilla-model",
            model_match=False,
            reusable=False,
            detail="connection refused",
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ):
            snapshot = (
                runtime.inspect_configured_runtime(
                    (
                        "http://127.0.0.1:8080"
                        "/v1/chat/completions"
                    ),
                    "thrilla-model",
                )
            )

        self.assertFalse(snapshot.ready)
        self.assertEqual(
            (),
            snapshot.reported_models,
        )
        self.assertIn(
            "connection refused",
            snapshot.detail,
        )
        self.assertIn(
            "connection refused",
            snapshot.error,
        )

    def test_model_mismatch_is_visible(self):
        _, manager, health = self._modules()

        runtime = manager.RuntimeManager(
            health_timeout=0.5
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("wrong-model",),
            expected_model="expected-model",
            model_match=False,
            reusable=False,
            detail="expected model not available",
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ):
            snapshot = (
                runtime.inspect_configured_runtime(
                    (
                        "http://127.0.0.1:8080"
                        "/v1/chat/completions"
                    ),
                    "expected-model",
                )
            )

        self.assertFalse(snapshot.ready)
        self.assertEqual(
            "expected-model",
            snapshot.expected_model,
        )
        self.assertEqual(
            ("wrong-model",),
            snapshot.reported_models,
        )
        self.assertIn(
            "expected model not available",
            snapshot.detail,
        )

    def test_configured_health_timeout_is_used(self):
        _, manager, health = self._modules()

        runtime = manager.RuntimeManager(
            health_timeout=1.25
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8181,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("timeout-model",),
            expected_model="timeout-model",
            model_match=True,
            reusable=True,
            detail="ready",
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ) as inspector:
            runtime.inspect_configured_runtime(
                (
                    "http://127.0.0.1:8181"
                    "/v1/chat/completions"
                ),
                "timeout-model",
            )

        inspector.assert_called_once_with(
            host="127.0.0.1",
            port=8181,
            timeout=1.25,
            expected_model="timeout-model",
        )


if __name__ == "__main__":
    unittest.main()
