"""Structured llama-server command construction."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class RuntimeCommandConfig:
    """Configuration used to construct one llama-server invocation."""

    executable: str
    model: str
    alias: str
    host: str
    port: int
    context_size: Optional[int]
    parallel_slots: Optional[int]
    extra_args: Tuple[str, ...] = ()


def build_llama_server_command(
    config: RuntimeCommandConfig,
) -> List[str]:
    """Build llama-server argv without shell-string interpolation."""
    command = [
        config.executable,
        "-m",
        config.model,
        "-a",
        config.alias,
        "--host",
        config.host,
        "--port",
        str(config.port),
    ]

    if config.context_size is not None:
        command.extend(
            [
                "-c",
                str(config.context_size),
            ]
        )

    if config.parallel_slots is not None:
        command.extend(
            [
                "-np",
                str(config.parallel_slots),
            ]
        )

    command.extend(config.extra_args)

    return command
