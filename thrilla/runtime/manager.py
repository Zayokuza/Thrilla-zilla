"""Runtime lifecycle to LocalModelClient integration boundary."""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from ..model import LocalModelClient
from .health import ExistingServerInspection, inspect_existing_server
from .process import (
    ProcessOwnership,
    RuntimeProcessRecord,
)


class RuntimeBindingError(RuntimeError):
    """Raised when runtime identity cannot safely become a client binding."""


@dataclass(frozen=True)
class RuntimeClientBinding:
    """Inference client bound to one observed runtime identity."""

    host: str
    port: int
    model: str
    ownership: ProcessOwnership
    detail: str
    client: LocalModelClient


class RuntimeManager:
    """Connect verified runtime identities to inference clients."""

    def __init__(
        self,
        request_timeout: Optional[float] = 90.0,
        remote_policy: object = False,
        health_timeout: Optional[float] = None,
    ) -> None:
        self.request_timeout = request_timeout
        self.remote_policy = remote_policy
        self.health_timeout = health_timeout

    @classmethod
    def from_config(
        cls,
        config: object,
    ) -> "RuntimeManager":
        """Construct client policy from Universal Limit Control."""
        request_timeout = config.resolve_limit(
            "model.request_timeout"
        ).value

        remote_policy = config.resolve_limit(
            "network.remote_model"
        ).value

        health_timeout = config.resolve_limit(
            "runtime.health_timeout",
            auto_value=0.5,
        ).value

        return cls(
            request_timeout=request_timeout,
            remote_policy=remote_policy,
            health_timeout=health_timeout,
        )

    def _make_client(
        self,
        url: str,
        model: str,
    ) -> LocalModelClient:
        return LocalModelClient(
            url,
            model,
            self.request_timeout,
            remote_policy=self.remote_policy,
        )

    def ready_binding(
        self,
        model_url: str,
        expected_model: str,
    ) -> RuntimeClientBinding:
        """Inspect the configured local endpoint before inference."""
        parsed = urlparse(model_url)

        if parsed.scheme != "http" or not parsed.hostname:
            raise RuntimeBindingError(
                "configured local runtime URL is invalid: {0}".format(
                    model_url
                )
            )

        try:
            port = parsed.port
        except ValueError as error:
            raise RuntimeBindingError(
                "configured local runtime port is invalid"
            ) from error

        if port is None:
            port = 80

        inspection = inspect_existing_server(
            host=parsed.hostname,
            port=port,
            timeout=self.health_timeout,
            expected_model=expected_model,
        )

        return self.bind_external(inspection)

    def bind_external(
        self,
        inspection: ExistingServerInspection,
    ) -> RuntimeClientBinding:
        """Bind one observed external OpenAI-compatible runtime."""
        if not inspection.reusable:
            raise RuntimeBindingError(
                "external runtime is not reusable: {0}".format(
                    inspection.detail
                )
            )

        model = (
            inspection.expected_model
            or (
                inspection.models[0]
                if inspection.models
                else ""
            )
        )

        url = "http://{0}:{1}/v1/chat/completions".format(
            inspection.host,
            inspection.port,
        )

        client = self._make_client(
            url,
            model,
        )

        return RuntimeClientBinding(
            host=inspection.host,
            port=inspection.port,
            model=model,
            ownership=ProcessOwnership.EXTERNAL,
            detail=inspection.detail,
            client=client,
        )


    def bind_managed(
        self,
        record: RuntimeProcessRecord,
        host: str,
        model_id: str,
    ) -> RuntimeClientBinding:
        """Bind one Thrilla-managed runtime to its inference adapter."""
        if (
            record.ownership
            != ProcessOwnership.THRILLA_MANAGED
        ):
            raise RuntimeBindingError(
                "runtime record is not Thrilla-managed"
            )

        url = "http://{0}:{1}/v1/chat/completions".format(
            host,
            record.port,
        )

        client = self._make_client(
            url,
            model_id,
        )

        return RuntimeClientBinding(
            host=host,
            port=record.port,
            model=model_id,
            ownership=record.ownership,
            detail="Thrilla-managed runtime binding",
            client=client,
        )
