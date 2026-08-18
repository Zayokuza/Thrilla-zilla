import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from thrilla.runtime.manager import RuntimeBindingError
from thrilla.runtime.process import ProcessOwnership
from thrilla.runtime.supervisor import RuntimeSupervisor


class RuntimeSupervisorTests(unittest.TestCase):
    def _config(self, root, model_path):
        return SimpleNamespace(
            model_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="local-model",
            preferred_model_path=str(model_path),
            state_path=Path(root),
            runtime_autostart=True,
            runtime_context=2048,
            runtime_threads=4,
            runtime_start_timeout=3.0,
            runtime_stop_timeout=2.0,
        )

    def test_existing_runtime_is_reused_without_spawn(self):
        with tempfile.TemporaryDirectory() as root:
            model_path = Path(root) / "model.gguf"
            model_path.write_bytes(b"GGUF")
            config = self._config(root, model_path)
            binding = object()
            manager = Mock()
            manager.ready_binding.return_value = binding
            supervisor = RuntimeSupervisor(config, manager)
            with patch("thrilla.runtime.supervisor.spawn_managed_process") as spawn:
                self.assertIs(supervisor.ensure_ready(), binding)
            spawn.assert_not_called()

    def test_missing_runtime_autostarts_preferred_model(self):
        with tempfile.TemporaryDirectory() as root:
            model_path = Path(root) / "model.gguf"
            model_path.write_bytes(b"GGUF")
            config = self._config(root, model_path)
            manager = Mock()
            manager.ready_binding.side_effect = RuntimeBindingError("connection refused")
            manager.inspect_configured_runtime.return_value = SimpleNamespace(
                ready=True, detail="ready"
            )
            expected_binding = object()
            manager.bind_managed.return_value = expected_binding

            process = Mock()
            process.pid = 1234
            process.poll.return_value = None
            record = SimpleNamespace(
                ownership=ProcessOwnership.THRILLA_MANAGED,
                pid=1234,
                port=8080,
                owner_token="token",
            )
            handle = SimpleNamespace(record=record, process=process)
            supervisor = RuntimeSupervisor(config, manager)

            with patch(
                "thrilla.runtime.supervisor.find_llama_server",
                return_value="/usr/bin/llama-server",
            ), patch(
                "thrilla.runtime.supervisor.spawn_managed_process",
                return_value=handle,
            ) as spawn:
                binding = supervisor.ensure_ready()

            self.assertIs(binding, expected_binding)
            command = spawn.call_args.kwargs["command"]
            self.assertIn("/usr/bin/llama-server", command)
            self.assertIn(str(model_path), command)
            self.assertIn("--alias", command)
            self.assertIn("local-model", command)
            self.assertIn("--port", command)
            self.assertIn("8080", command)
            manager.bind_managed.assert_called_once_with(
                record, "127.0.0.1", "local-model"
            )

    def test_autostart_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            model_path = Path(root) / "model.gguf"
            model_path.write_bytes(b"GGUF")
            config = self._config(root, model_path)
            config.runtime_autostart = False
            manager = Mock()
            manager.ready_binding.side_effect = RuntimeBindingError("connection refused")
            supervisor = RuntimeSupervisor(config, manager)
            with self.assertRaises(RuntimeBindingError):
                supervisor.ensure_ready()

    def test_missing_preferred_model_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            config = self._config(root, Path(root) / "missing.gguf")
            manager = Mock()
            manager.ready_binding.side_effect = RuntimeBindingError("connection refused")
            supervisor = RuntimeSupervisor(config, manager)
            with self.assertRaisesRegex(RuntimeBindingError, "preferred model"):
                supervisor.ensure_ready()


if __name__ == "__main__":
    unittest.main()
