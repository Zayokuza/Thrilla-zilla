"""Automatic local llama-server lifecycle supervision."""

import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from ..model import ModelError
from .discovery import find_llama_server
from .manager import RuntimeBindingError, RuntimeClientBinding, RuntimeManager
from .process import (
    ManagedProcessHandle,
    ShutdownResult,
    shutdown_managed_process,
    spawn_managed_process,
)

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class RuntimeSupervisor:
    """Reuse a healthy runtime or safely start Thrilla's preferred model."""

    def __init__(self, config: object, manager: RuntimeManager) -> None:
        self.config = config
        self.manager = manager
        self._handle: Optional[ManagedProcessHandle] = None
        self._binding: Optional[RuntimeClientBinding] = None
        self._binding_key = None

    def _current_binding_key(self):
        return (
            id(self.manager),
            str(self.config.model_url),
            str(self.config.model_name),
        )

    def _remember_binding(
        self,
        binding: RuntimeClientBinding,
    ) -> RuntimeClientBinding:
        self._binding = binding
        self._binding_key = self._current_binding_key()
        return binding

    def _clear_binding(self) -> None:
        self._binding = None
        self._binding_key = None

    @property
    def managed_handle(self) -> Optional[ManagedProcessHandle]:
        return self._handle

    def _endpoint(self):
        parsed = urlparse(self.config.model_url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise RuntimeBindingError("configured local runtime URL is invalid")
        try:
            port = parsed.port
        except ValueError as error:
            raise RuntimeBindingError("configured local runtime port is invalid") from error
        if port is None:
            port = 80
        return parsed.hostname, port

    def _log_path(self) -> Path:
        return Path(self.config.state_path) / "runtime" / "llama-server.log"

    def _tail_log(self, lines: int = 30) -> str:
        try:
            content = self._log_path().read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            return ""
        return "\n".join(content[-lines:])

    def _command(self, executable: str, model_path: Path, host: str, port: int):
        return [
            executable,
            "-m",
            str(model_path),
            "--alias",
            str(self.config.model_name),
            "--host",
            host,
            "--port",
            str(port),
            "-c",
            str(self.config.runtime_context),
            "-t",
            str(self.config.runtime_threads),
            "--cache-ram",
            "256",
        ]

    def ensure_ready(self) -> RuntimeClientBinding:
        """Return a verified binding, autostarting a local runtime if needed."""
        key = self._current_binding_key()

        if (
            self._binding is not None
            and self._binding_key == key
        ):
            return self._binding

        self._clear_binding()

        try:
            binding = self.manager.ready_binding(
                self.config.model_url,
                self.config.model_name,
            )
            return self._remember_binding(binding)
        except RuntimeBindingError as initial_error:
            if not self.config.runtime_autostart:
                raise

            host, port = self._endpoint()
            if host.lower() not in _LOCAL_HOSTS:
                raise initial_error

            model_path = Path(self.config.preferred_model_path).expanduser()
            if not model_path.is_file():
                raise RuntimeBindingError(
                    "Thrilla runtime is unavailable and the preferred model "
                    "does not exist: {0}".format(model_path)
                ) from initial_error

            executable = find_llama_server()
            if not executable:
                raise RuntimeBindingError(
                    "Thrilla runtime is unavailable and llama-server was not found in PATH"
                ) from initial_error

            if self._handle is not None and self._handle.process.poll() is None:
                raise RuntimeBindingError(
                    "Thrilla-managed runtime is still starting but has not become reusable"
                ) from initial_error

            command = self._command(executable, model_path, host, port)
            self._handle = spawn_managed_process(
                command=command,
                model=str(model_path),
                port=port,
                log_path=str(self._log_path()),
            )

            deadline = time.monotonic() + float(self.config.runtime_start_timeout)
            while time.monotonic() < deadline:
                if self._handle.process.poll() is not None:
                    detail = self._tail_log()
                    raise RuntimeBindingError(
                        "Thrilla-managed llama-server exited during startup"
                        + (("\n" + detail) if detail else "")
                    )

                snapshot = self.manager.inspect_configured_runtime(
                    self.config.model_url,
                    self.config.model_name,
                )
                if snapshot.ready:
                    binding = self.manager.bind_managed(
                        self._handle.record,
                        host,
                        self.config.model_name,
                    )
                    return self._remember_binding(
                        binding
                    )
                time.sleep(0.25)

            self.shutdown()
            detail = self._tail_log()
            raise RuntimeBindingError(
                "Thrilla-managed llama-server did not become ready within {0:.1f} seconds".format(
                    float(self.config.runtime_start_timeout)
                )
                + (("\n" + detail) if detail else "")
            )

    def chat(self, messages, route: str) -> str:
        """Run inference and recover once from a crashed managed runtime."""
        binding = self.ensure_ready()
        try:
            return binding.client.chat(messages, route)
        except ModelError:
            self._clear_binding()

            if (
                self._handle is None
                or self._handle.process.poll() is None
            ):
                raise

            self._handle = None
            recovered = self.ensure_ready()
            return recovered.client.chat(
                messages,
                route,
            )

    def shutdown(self) -> Optional[ShutdownResult]:
        """Stop only the runtime process owned by this supervisor."""
        self._clear_binding()

        if self._handle is None:
            return None
        handle = self._handle
        self._handle = None
        return shutdown_managed_process(
            handle,
            handle.record.owner_token,
            timeout=float(self.config.runtime_stop_timeout),
        )
