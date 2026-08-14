import tempfile
import unittest
from unittest.mock import MagicMock

from thrilla.app import ThrillaApp
from thrilla.config import Config


class LimitIntegrationTests(unittest.TestCase):
    def test_model_client_uses_resolved_request_timeout(self):
        config = Config.defaults()
        config.request_timeout = 90.0
        config.limit_default_mode = "on"
        config.limit_values = {
            "model.request_timeout": 135.0,
        }

        app = ThrillaApp(config)

        self.assertEqual(
            135.0,
            app.model.timeout,
            "LocalModelClient must use the resolved Limit Control timeout.",
        )

    def test_model_timeout_off_removes_thrilla_timeout(self):
        config = Config.defaults()
        config.request_timeout = 90.0
        config.limit_modes = {
            "model.request_timeout": "off",
        }

        app = ThrillaApp(config)

        self.assertIsNone(
            app.model.timeout,
            "OFF must remove Thrilla's model request timeout.",
        )

    def test_chat_uses_resolved_history_turn_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Config.defaults()
            config.state_root = temporary
            config.limit_default_mode = "on"
            config.limit_values = {
                "memory.history_turns": 1,
            }

            app = ThrillaApp(config)
            app.history.messages = MagicMock(return_value=[])
            app.history.append = MagicMock()
            app.model.chat = MagicMock(return_value="working")
            app._input_line = MagicMock(side_effect=["hello", "back"])
            app._header = MagicMock()

            app.ask()

            app.history.messages.assert_called_once_with(1)

    def test_history_turn_limit_off_passes_no_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Config.defaults()
            config.state_root = temporary
            config.limit_modes = {
                "memory.history_turns": "off",
            }

            app = ThrillaApp(config)
            app.history.messages = MagicMock(return_value=[])
            app.history.append = MagicMock()
            app.model.chat = MagicMock(return_value="working")
            app._input_line = MagicMock(side_effect=["hello", "back"])
            app._header = MagicMock()

            app.ask()

            app.history.messages.assert_called_once_with(None)

    def test_donor_inspection_uses_resolved_git_timeout(self):
        config = Config.defaults()
        config.limit_default_mode = "on"
        config.limit_values = {
            "donor.git_timeout": 9.0,
        }

        app = ThrillaApp(config)

        spec = MagicMock()
        spec.repository = "example/repository"

        state = MagicMock()
        state.path = "/tmp/example"
        state.state = "ready"
        state.present = True

        details = MagicMock()
        details.error = ""
        details.branch = "main"
        details.commit = "abc123"
        details.clean = True
        details.remote = "https://example.invalid/repository.git"

        app._prompt = MagicMock(return_value="example")
        app._find_specs = MagicMock(return_value=[spec])
        app.registry.inspect = MagicMock(return_value=state)
        app.registry.verify_git = MagicMock(return_value=details)
        app._status = MagicMock()
        app._pause = MagicMock()
        app.audit.write = MagicMock()

        app.inspect_donor()

        app.registry.verify_git.assert_called_once_with(
            spec,
            timeout=9.0,
        )

    def test_donor_git_timeout_off_passes_no_timeout(self):
        config = Config.defaults()
        config.limit_modes = {
            "donor.git_timeout": "off",
        }

        app = ThrillaApp(config)

        spec = MagicMock()
        spec.repository = "example/repository"

        state = MagicMock()
        state.path = "/tmp/example"
        state.state = "ready"
        state.present = True

        details = MagicMock()
        details.error = ""
        details.branch = "main"
        details.commit = "abc123"
        details.clean = True
        details.remote = "https://example.invalid/repository.git"

        app._prompt = MagicMock(return_value="example")
        app._find_specs = MagicMock(return_value=[spec])
        app.registry.inspect = MagicMock(return_value=state)
        app.registry.verify_git = MagicMock(return_value=details)
        app._status = MagicMock()
        app._pause = MagicMock()
        app.audit.write = MagicMock()

        app.inspect_donor()

        app.registry.verify_git.assert_called_once_with(
            spec,
            timeout=None,
        )

    def test_remote_model_auto_remains_blocked_by_default(self):
        import os
        from unittest.mock import patch

        config = Config.defaults()
        config.model_url = "https://example.com/v1/chat/completions"

        with patch.dict(os.environ, {}, clear=True):
            app = ThrillaApp(config)

            with self.assertRaises(Exception):
                app.model._allow_url()

    def test_remote_model_on_with_true_value_allows_remote(self):
        import os
        from unittest.mock import patch

        config = Config.defaults()
        config.model_url = "https://example.com/v1/chat/completions"
        config.limit_modes = {
            "network.remote_model": "on",
        }
        config.limit_values = {
            "network.remote_model": True,
        }

        with patch.dict(os.environ, {}, clear=True):
            app = ThrillaApp(config)
            try:
                app.model._allow_url()
            except Exception as error:
                self.fail(
                    "Limit Control ON with value true must allow remote model: "
                    "{0}".format(error)
                )

    def test_remote_model_off_removes_thrilla_block(self):
        import os
        from unittest.mock import patch

        config = Config.defaults()
        config.model_url = "https://example.com/v1/chat/completions"
        config.limit_modes = {
            "network.remote_model": "off",
        }

        with patch.dict(os.environ, {}, clear=True):
            app = ThrillaApp(config)
            try:
                app.model._allow_url()
            except Exception as error:
                self.fail(
                    "Limit Control OFF must remove Thrilla remote-model block: "
                    "{0}".format(error)
                )


if __name__ == "__main__":
    unittest.main()
