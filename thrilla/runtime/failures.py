"""Structured runtime failure classification."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from .health import ModelsEndpointProbe, ReadinessResult
from .ports import PortInspection


class RuntimeFailureKind(str, Enum):
    """Stage-3 runtime failure categories."""

    EXECUTABLE_MISSING = "executable_missing"
    MODEL_MISSING = "model_missing"
    INVALID_GGUF = "invalid_gguf"
    INCOMPATIBLE_MODEL = "incompatible_model"
    PORT_OCCUPIED = "port_occupied"
    STARTUP_TIMEOUT = "startup_timeout"
    PROCESS_CRASH = "process_crash"
    MEMORY_FAILURE = "memory_failure"
    HTTP_HEALTH_FAILURE = "http_health_failure"
    MODEL_API_FAILURE = "model_api_failure"
    UNEXPECTED_EXIT = "unexpected_exit"
    PERMISSION_FAILURE = "permission_failure"


@dataclass(frozen=True)
class RuntimeFailure:
    """Actionable explanation for one runtime failure."""

    kind: RuntimeFailureKind
    what_failed: str
    why: str
    where: str
    attempted_recovery: str
    remaining_options: Tuple[str, ...]


def failure_from_spawn_exception(
    error: BaseException,
    where: str,
) -> RuntimeFailure:
    """Classify an exception raised while spawning a runtime."""
    if isinstance(error, FileNotFoundError):
        return RuntimeFailure(
            kind=RuntimeFailureKind.EXECUTABLE_MISSING,
            what_failed="runtime executable launch",
            why=str(error) or "runtime executable was not found",
            where=where,
            attempted_recovery="none",
            remaining_options=(
                "configure an existing executable",
                "install a compatible runtime executable",
            ),
        )

    if isinstance(error, PermissionError):
        return RuntimeFailure(
            kind=RuntimeFailureKind.PERMISSION_FAILURE,
            what_failed="runtime executable launch",
            why=str(error) or "permission was denied",
            where=where,
            attempted_recovery="none",
            remaining_options=(
                "inspect executable permissions",
                "select an executable Thrilla may run",
            ),
        )

    if isinstance(error, MemoryError):
        return RuntimeFailure(
            kind=RuntimeFailureKind.MEMORY_FAILURE,
            what_failed="runtime process allocation",
            why=str(error) or "memory allocation failed",
            where=where,
            attempted_recovery="none",
            remaining_options=(
                "select a smaller model",
                "reduce runtime resource requirements",
            ),
        )

    return RuntimeFailure(
        kind=RuntimeFailureKind.UNEXPECTED_EXIT,
        what_failed="runtime executable launch",
        why=str(error) or type(error).__name__,
        where=where,
        attempted_recovery="none",
        remaining_options=(
            "inspect runtime logs",
            "retry after correcting the reported cause",
        ),
    )

def failure_from_port_inspection(
    status: PortInspection,
) -> Optional[RuntimeFailure]:
    """Return a port conflict failure when the address cannot be bound."""
    if status.bindable:
        return None

    return RuntimeFailure(
        kind=RuntimeFailureKind.PORT_OCCUPIED,
        what_failed="runtime port allocation",
        why="configured TCP address is not available for binding",
        where="{0}:{1}".format(
            status.host,
            status.port,
        ),
        attempted_recovery="inspected configured port",
        remaining_options=(
            "reuse compatible existing service",
            "select another permitted port",
        ),
    )

def failure_from_readiness(
    result: ReadinessResult,
    where: str,
) -> Optional[RuntimeFailure]:
    """Classify a failed readiness wait."""
    if result.ready:
        return None

    if result.timed_out:
        return RuntimeFailure(
            kind=RuntimeFailureKind.STARTUP_TIMEOUT,
            what_failed="model runtime readiness",
            why=(
                "startup deadline expired after "
                "{0} health attempts; last detail: {1}"
            ).format(
                result.attempts,
                result.detail,
            ),
            where=where,
            attempted_recovery="repeated /v1/models health polling",
            remaining_options=(
                "inspect startup log",
                "retry managed startup",
                "select a lighter model or runtime configuration",
            ),
        )

    return RuntimeFailure(
        kind=RuntimeFailureKind.HTTP_HEALTH_FAILURE,
        what_failed="model runtime readiness",
        why=result.detail or "runtime did not become ready",
        where=where,
        attempted_recovery="health inspection",
        remaining_options=(
            "inspect process status",
            "inspect runtime log",
        ),
    )

def failure_from_models_probe(
    probe: ModelsEndpointProbe,
) -> Optional[RuntimeFailure]:
    """Classify a failure observed from /v1/models."""
    if not probe.reachable:
        return RuntimeFailure(
            kind=RuntimeFailureKind.HTTP_HEALTH_FAILURE,
            what_failed="runtime HTTP health connection",
            why=probe.detail or "runtime endpoint was unreachable",
            where=probe.url,
            attempted_recovery="queried /v1/models",
            remaining_options=(
                "inspect process status",
                "inspect port status",
                "retry health check",
            ),
        )

    if not probe.openai_compatible:
        return RuntimeFailure(
            kind=RuntimeFailureKind.MODEL_API_FAILURE,
            what_failed="runtime model API",
            why=probe.detail or "unexpected /v1/models response",
            where=probe.url,
            attempted_recovery="queried /v1/models",
            remaining_options=(
                "inspect server API compatibility",
                "select a compatible runtime service",
            ),
        )

    if (
        probe.expected_model
        and not probe.model_match
    ):
        return RuntimeFailure(
            kind=RuntimeFailureKind.INCOMPATIBLE_MODEL,
            what_failed="expected runtime model",
            why=(
                "expected model {0!r} was not reported; "
                "available models: {1}"
            ).format(
                probe.expected_model,
                ", ".join(probe.models) or "none",
            ),
            where=probe.url,
            attempted_recovery="inspected /v1/models inventory",
            remaining_options=(
                "load the expected model",
                "select a compatible existing model service",
            ),
        )

    return None



def failure_from_process_returncode(
    returncode: Optional[int],
    where: str,
) -> Optional[RuntimeFailure]:
    """Classify an observed managed-process exit status."""
    if returncode is None:
        return None

    if returncode < 0:
        return RuntimeFailure(
            kind=RuntimeFailureKind.PROCESS_CRASH,
            what_failed="managed runtime process",
            why="process terminated by signal {0}".format(
                -returncode
            ),
            where=where,
            attempted_recovery="captured process exit status",
            remaining_options=(
                "inspect startup/runtime log",
                "evaluate crash retry policy",
            ),
        )

    return RuntimeFailure(
        kind=RuntimeFailureKind.UNEXPECTED_EXIT,
        what_failed="managed runtime process",
        why="process exited with status {0}".format(
            returncode
        ),
        where=where,
        attempted_recovery="captured process exit status",
        remaining_options=(
            "inspect startup/runtime log",
            "restart if runtime policy permits",
        ),
    )

def inspect_model_file_failure(
    path: Path,
) -> Optional[RuntimeFailure]:
    """Inspect model existence, readability, and GGUF file magic."""
    candidate = Path(path)

    if not candidate.is_file():
        return RuntimeFailure(
            kind=RuntimeFailureKind.MODEL_MISSING,
            what_failed="local model discovery",
            why="configured model file does not exist",
            where=str(candidate),
            attempted_recovery="checked model path",
            remaining_options=(
                "select an existing local model",
                "rescan local model inventory",
            ),
        )

    try:
        with candidate.open("rb") as handle:
            magic = handle.read(4)
    except PermissionError as error:
        return RuntimeFailure(
            kind=RuntimeFailureKind.PERMISSION_FAILURE,
            what_failed="local model read",
            why=str(error) or "permission was denied",
            where=str(candidate),
            attempted_recovery="opened model for GGUF inspection",
            remaining_options=(
                "inspect model file permissions",
                "select a readable model",
            ),
        )

    if magic != b"GGUF":
        return RuntimeFailure(
            kind=RuntimeFailureKind.INVALID_GGUF,
            what_failed="local model validation",
            why="file does not begin with GGUF magic",
            where=str(candidate),
            attempted_recovery="inspected model file header",
            remaining_options=(
                "select a valid GGUF model",
                "replace or re-download the model file",
            ),
        )

    return None
