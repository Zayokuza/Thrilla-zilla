"""Truthful snapshot of the configured local runtime."""

from dataclasses import dataclass
from typing import Optional, Tuple

from .process import ProcessOwnership


@dataclass(frozen=True)
class RuntimeStatusSnapshot:
    """Immutable observed status of the configured runtime."""

    configured_endpoint: str
    expected_model: str
    ready: bool
    detail: str
    host: str = ""
    port: Optional[int] = None
    ownership: Optional[ProcessOwnership] = None
    reported_models: Tuple[str, ...] = ()
    error: str = ""
