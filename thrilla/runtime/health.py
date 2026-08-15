"""Inspection of existing OpenAI-compatible local model services."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

from .ports import inspect_port


@dataclass(frozen=True)
class ModelsEndpointProbe:
    """Observed result from one /v1/models request."""

    url: str
    reachable: bool
    openai_compatible: bool
    models: Tuple[str, ...]
    detail: str
    expected_model: str = ""
    model_match: bool = True



@dataclass(frozen=True)
class ExistingServerInspection:
    """Observed compatibility of an already-running local service."""

    host: str
    port: int
    listening: bool
    bindable: bool
    openai_compatible: bool
    models: Tuple[str, ...]
    expected_model: str
    model_match: bool
    reusable: bool
    detail: str

def probe_models_endpoint(
    host: str,
    port: int,
    timeout: float = 0.5,
    expected_model: Optional[str] = None,
) -> ModelsEndpointProbe:
    """Query an existing service's OpenAI-compatible models endpoint."""
    url = "http://{0}:{1}/v1/models".format(
        host,
        port,
    )

    request = urllib.request.Request(
        url,
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )
    except urllib.error.HTTPError as error:
        return ModelsEndpointProbe(
            url=url,
            reachable=True,
            openai_compatible=False,
            models=(),
            detail="HTTP {0}".format(
                error.code
            ),
        )
    except (
        OSError,
        ValueError,
        urllib.error.URLError,
    ) as error:
        return ModelsEndpointProbe(
            url=url,
            reachable=False,
            openai_compatible=False,
            models=(),
            detail=str(error),
        )

    if (
        not isinstance(payload, dict)
        or "data" not in payload
        or not isinstance(
            payload["data"],
            list,
        )
    ):
        return ModelsEndpointProbe(
            url=url,
            reachable=True,
            openai_compatible=False,
            models=(),
            detail="unexpected /v1/models payload",
        )

    data = payload["data"]

    models = tuple(
        item.get(
            "id",
            "",
        )
        for item in data
        if isinstance(item, dict)
        and isinstance(
            item.get("id"),
            str,
        )
        and item.get("id")
    )

    expected = expected_model or ""

    return ModelsEndpointProbe(
        url=url,
        reachable=True,
        openai_compatible=True,
        models=models,
        detail="models endpoint responded",
        expected_model=expected,
        model_match=(
            not expected
            or expected in models
        ),
    )

def inspect_existing_server(
    host: str,
    port: int,
    timeout: float = 0.5,
    expected_model: Optional[str] = None,
) -> ExistingServerInspection:
    """Inspect an existing listener without assuming process ownership."""
    port_status = inspect_port(
        host,
        port,
        timeout=timeout,
    )

    probe = probe_models_endpoint(
        host,
        port,
        timeout=timeout,
        expected_model=expected_model,
    )

    reusable = (
        port_status.listening
        and probe.openai_compatible
        and probe.model_match
    )

    return ExistingServerInspection(
        host=host,
        port=port,
        listening=port_status.listening,
        bindable=port_status.bindable,
        openai_compatible=probe.openai_compatible,
        models=probe.models,
        expected_model=probe.expected_model,
        model_match=probe.model_match,
        reusable=reusable,
        detail=probe.detail,
    )
