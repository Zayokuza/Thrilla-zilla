"""Runtime process ownership metadata."""

import hmac
import secrets
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Sequence, Tuple


class ProcessOwnership(str, Enum):
    """Whether a runtime process belongs to Thrilla."""

    EXTERNAL = "EXTERNAL"
    THRILLA_MANAGED = "THRILLA_MANAGED"

@dataclass(frozen=True)
class RuntimeProcessRecord:
    """Metadata describing one runtime process."""

    ownership: ProcessOwnership
    pid: int
    executable: str
    command: Tuple[str, ...]
    model: str
    port: int
    start_time: str
    owner_token: str
    log_path: str




@dataclass(frozen=True)
class ManagedProcessHandle:
    """Live child handle paired with Thrilla ownership metadata."""

    record: RuntimeProcessRecord
    process: subprocess.Popen

def can_control_process(
    record: RuntimeProcessRecord,
    owner_token: str,
) -> bool:
    """Return whether Thrilla may control this process."""
    return (
        record.ownership
        == ProcessOwnership.THRILLA_MANAGED
        and bool(record.owner_token)
        and bool(owner_token)
        and hmac.compare_digest(
            record.owner_token,
            owner_token,
        )
    )

def spawn_managed_process(
    command: Sequence[str],
    model: str,
    port: int,
    log_path: str,
) -> ManagedProcessHandle:
    """Spawn one Thrilla-managed runtime child process."""
    command_tuple = tuple(command)

    if not command_tuple:
        raise ValueError(
            "command must not be empty"
        )

    log_file_path = Path(log_path)

    log_file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = log_file_path.open(
        "ab"
    )

    try:
        child = subprocess.Popen(
            list(command_tuple),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=False,
        )
    finally:
        log_file.close()

    record = RuntimeProcessRecord(
        ownership=ProcessOwnership.THRILLA_MANAGED,
        pid=child.pid,
        executable=command_tuple[0],
        command=command_tuple,
        model=model,
        port=port,
        start_time=datetime.now().astimezone().isoformat(),
        owner_token=secrets.token_urlsafe(32),
        log_path=log_path,
    )

    return ManagedProcessHandle(
        record=record,
        process=child,
    )
