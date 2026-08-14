"""Universal Limit Control for Thrilla-zilla."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional, Tuple


class LimitMode(str, Enum):
    """How a Thrilla-created software limit is applied."""

    ON = "on"
    AUTO = "auto"
    OFF = "off"


@dataclass(frozen=True)
class LimitSpec:
    """Definition of one Thrilla-controlled software limit."""

    name: str
    default_mode: LimitMode
    default_value: object = None
    description: str = ""


@dataclass(frozen=True)
class LimitDecision:
    """Resolved value and explanation for one limit."""

    name: str
    mode: LimitMode
    value: object
    source: str
    explanation: str


class LimitRegistry:
    """Registry of named Thrilla software limits."""

    def __init__(self, specs: Iterable[LimitSpec]) -> None:
        registered: Dict[str, LimitSpec] = {}

        for spec in specs:
            if spec.name in registered:
                raise ValueError(
                    "duplicate limit name: {0}".format(spec.name)
                )
            registered[spec.name] = spec

        self._specs = registered

    def get(self, name: str) -> LimitSpec:
        return self._specs[name]

    def names(self) -> Tuple[str, ...]:
        return tuple(self._specs.keys())

    def resolve(
        self,
        name: str,
        mode: Optional[LimitMode] = None,
        configured_value: object = None,
        auto_value: object = None,
    ) -> LimitDecision:
        spec = self.get(name)
        resolved_mode = spec.default_mode if mode is None else mode

        if not isinstance(resolved_mode, LimitMode):
            resolved_mode = LimitMode(resolved_mode)

        if resolved_mode is LimitMode.OFF:
            return LimitDecision(
                name=name,
                mode=resolved_mode,
                value=None,
                source="off",
                explanation=(
                    "{0} is OFF; Thrilla imposes no software limit."
                ).format(name),
            )

        if resolved_mode is LimitMode.ON:
            if configured_value is not None:
                value = configured_value
                source = "configured"
            else:
                value = spec.default_value
                source = "default"

            return LimitDecision(
                name=name,
                mode=resolved_mode,
                value=value,
                source=source,
                explanation=(
                    "{0} is ON using its {1} value."
                ).format(name, source),
            )

        if auto_value is not None:
            value = auto_value
            source = "auto"
        else:
            value = spec.default_value
            source = "default"

        return LimitDecision(
            name=name,
            mode=resolved_mode,
            value=value,
            source=source,
            explanation=(
                "{0} is AUTO using its {1} value."
            ).format(name, source),
        )


_REQUIRED_LIMIT_NAMES = (
    "runtime.managed_startup",
    "runtime.startup_timeout",
    "runtime.health_timeout",
    "runtime.shutdown_timeout",
    "runtime.restart_limit",
    "runtime.crash_retry_limit",
    "runtime.model_size",
    "runtime.context_size",
    "runtime.batch_size",
    "runtime.parallel_slots",
    "runtime.cpu_threads",
    "runtime.gpu_layers",
    "runtime.ram_budget",
    "runtime.process_count",
    "runtime.queue_depth",
    "runtime.request_timeout",
    "runtime.response_tokens",
    "runtime.model_switch_frequency",
    "runtime.keep_alive",
    "runtime.idle_shutdown",
    "model.request_timeout",
    "memory.history_turns",
    "network.remote_model",
    "donor.git_timeout",
)


_DEFAULT_VALUES = {
    "model.request_timeout": 90.0,
    "memory.history_turns": 12,
    "network.remote_model": False,
    "donor.git_timeout": 4.0,
}


DEFAULT_LIMITS = LimitRegistry(
    tuple(
        LimitSpec(
            name=name,
            default_mode=LimitMode.AUTO,
            default_value=_DEFAULT_VALUES.get(name),
            description=(
                "Thrilla Limit Control setting for {0}."
            ).format(name),
        )
        for name in _REQUIRED_LIMIT_NAMES
    )
)
