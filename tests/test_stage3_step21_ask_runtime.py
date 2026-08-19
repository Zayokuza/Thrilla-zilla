import tempfile
import unittest
from unittest.mock import Mock, patch

from thrilla.app import ThrillaApp
from thrilla.config import Config
from thrilla.runtime.health import ExistingServerInspection
from thrilla.runtime.manager import RuntimeManager


class Step21AskRuntimeTests(unittest.TestCase):
    def test_thrilla_app_constructs_runtime_manager_from_config(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config = Config(
                donor_root=tempdir,
                state_root=tempdir,
                request_timeout=12.5,
            )

            app = ThrillaApp(config)
            self.addCleanup(app.close)

            self.assertTrue(
                hasattr(app, "runtime_manager"),
                "ThrillaApp must own a RuntimeManager",
            )
            self.assertIsInstance(app.runtime_manager, RuntimeManager)
            self.assertEqual(app.runtime_manager.request_timeout, 12.5)
            self.assertFalse(app.runtime_manager.remote_policy)


class Step21RuntimeReadinessTests(unittest.TestCase):
    def test_runtime_manager_can_bind_configured_ready_endpoint(self):
        manager = RuntimeManager(
            request_timeout=12.5,
            remote_policy=False,
        )

        inspection = ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("local-model",),
            expected_model="local-model",
            model_match=True,
            reusable=True,
            detail="models endpoint responded",
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ) as inspect:
            binding = manager.ready_binding(
                "http://127.0.0.1:8080/v1/chat/completions",
                "local-model",
            )

        inspect.assert_called_once_with(
            host="127.0.0.1",
            port=8080,
            timeout=None,
            expected_model="local-model",
        )
        self.assertEqual(binding.host, "127.0.0.1")
        self.assertEqual(binding.port, 8080)
        self.assertEqual(binding.model, "local-model")


class Step21AskBindingTests(unittest.TestCase):
    def test_ask_uses_runtime_manager_binding_client_for_inference(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config = Config(
                donor_root=tempdir,
                state_root=tempdir,
                save_history=False,
            )
            app = ThrillaApp(config)
            self.addCleanup(app.close)

            direct_client = Mock()
            direct_client.chat.return_value = "wrong client"
            app.model = direct_client

            bound_client = Mock()
            bound_client.chat.return_value = "bound answer"

            binding = Mock()
            binding.client = bound_client

            app.runtime_manager = Mock()
            app.runtime_manager.ready_binding.return_value = binding

            with patch.object(app, "_header"), patch.object(
                app,
                "_input_line",
                side_effect=["hello thrilla", "/back"],
            ):
                app.ask()

            app.runtime_manager.ready_binding.assert_called_once_with(
                config.model_url,
                config.model_name,
            )
            bound_client.chat.assert_called_once()
            direct_client.chat.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class Step21ReadinessFailureTests(unittest.TestCase):
    def test_readiness_failure_blocks_chat_and_completed_audit(self):
        from thrilla.runtime.manager import RuntimeBindingError

        with tempfile.TemporaryDirectory() as tempdir:
            config = Config(
                donor_root=tempdir,
                state_root=tempdir,
                save_history=False,
            )
            app = ThrillaApp(config)
            self.addCleanup(app.close)

            direct_client = Mock()
            app.model = direct_client

            app.runtime_manager = Mock()
            app.runtime_manager.ready_binding.side_effect = RuntimeBindingError(
                "external runtime is not reusable: connection refused"
            )

            app.audit = Mock()

            with patch.object(app, "_header"), patch.object(
                app,
                "_input_line",
                side_effect=["hello thrilla", "/back"],
            ):
                try:
                    app.ask()
                except RuntimeBindingError as error:
                    self.fail(
                        "Ask must handle runtime readiness failure: "
                        + str(error)
                    )

            direct_client.chat.assert_not_called()

            events = [
                call.args[0]
                for call in app.audit.write.call_args_list
            ]

            self.assertIn(
                "model_request_failed",
                events,
            )
            self.assertNotIn(
                "model_request_completed",
                events,
            )


class Step21HealthTimeoutTests(unittest.TestCase):
    def test_runtime_manager_from_config_uses_health_timeout_limit(self):
        from thrilla.runtime.manager import RuntimeManager

        with tempfile.TemporaryDirectory() as tempdir:
            config = Config(
                donor_root=tempdir,
                state_root=tempdir,
                limit_default_mode="on",
                limit_values={
                    "model.request_timeout": 12.5,
                    "network.remote_model": False,
                    "runtime.health_timeout": 0.37,
                },
            )

            manager = RuntimeManager.from_config(
                config
            )

            self.assertEqual(
                manager.health_timeout,
                0.37,
            )


class Step21HealthInspectionTests(unittest.TestCase):
    def test_ready_binding_passes_health_timeout_to_inspection(self):
        from thrilla.runtime.health import ExistingServerInspection
        from thrilla.runtime.manager import RuntimeManager

        manager = RuntimeManager(
            health_timeout=0.37,
        )

        inspection = ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("local-model",),
            expected_model="local-model",
            model_match=True,
            reusable=True,
            detail="models endpoint responded",
        )

        with patch(
            "thrilla.runtime.manager.inspect_existing_server",
            return_value=inspection,
        ) as inspect:
            manager.ready_binding(
                "http://127.0.0.1:8080/v1/chat/completions",
                "local-model",
            )

        inspect.assert_called_once_with(
            host="127.0.0.1",
            port=8080,
            timeout=0.37,
            expected_model="local-model",
        )


class Step21NavigationTests(unittest.TestCase):
    def test_navigation_commands_never_request_runtime_readiness(self):
        from thrilla.colors import ColorMode, Palette

        commands = (
            "back",
            "/help",
            "/route",
            "/clear",
        )

        for command in commands:
            with self.subTest(command=command):
                app = ThrillaApp.__new__(
                    ThrillaApp
                )

                app.palette = Palette(
                    ColorMode.NEVER
                )
                app.runtime_manager = Mock()
                app.model = Mock()
                app.history = Mock()
                app.audit = Mock()

                app.history.clear.return_value = False

                inputs = (
                    [command]
                    if command == "back"
                    else [command, "/back"]
                )

                with patch.object(
                    app,
                    "_header",
                ), patch.object(
                    app,
                    "_input_line",
                    side_effect=inputs,
                ):
                    app.ask()

                app.runtime_manager.ready_binding.assert_not_called()
                app.model.chat.assert_not_called()
