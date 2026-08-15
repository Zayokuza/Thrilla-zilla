"""Runtime process ownership metadata."""

import hmac
import secrets
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence, Tuple


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


@dataclass(frozen=True)
class ShutdownResult:
    """Observed result from one managed shutdown request."""

    authorized: bool
    already_stopped: bool
    terminated: bool
    escalated: bool
    returncode: Optional[int]
    detail: str


@dataclass(frozen=True)
class OrphanInspection:
    """Observed relationship between managed metadata and a live child."""

    trusted: bool
    orphaned: bool
    running: bool
    pid_matches: bool
    returncode: Optional[int]
    detail: str

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

def shutdown_managed_process(
    handle: ManagedProcessHandle,
    owner_token: str,
    timeout: Optional[float],
) -> ShutdownResult:
    """Stop only a process whose Thrilla ownership is proven."""
    if handle.process.pid != handle.record.pid:
        return ShutdownResult(
            authorized=False,
            already_stopped=False,
            terminated=False,
            escalated=False,
            returncode=handle.process.poll(),
            detail="runtime PID proof rejected",
        )

    if not can_control_process(
        handle.record,
        owner_token,
    ):
        return ShutdownResult(
            authorized=False,
            already_stopped=False,
            terminated=False,
            escalated=False,
            returncode=handle.process.poll(),
            detail="runtime ownership proof rejected",
        )

    current_returncode = handle.process.poll()

    if current_returncode is not None:
        return ShutdownResult(
            authorized=True,
            already_stopped=True,
            terminated=False,
            escalated=False,
            returncode=current_returncode,
            detail="managed runtime was already stopped",
        )

    handle.process.terminate()

    try:
        returncode = handle.process.wait(
            timeout=timeout,
        )

        return ShutdownResult(
            authorized=True,
            already_stopped=False,
            terminated=True,
            escalated=False,
            returncode=returncode,
            detail="managed runtime terminated gracefully",
        )
    except subprocess.TimeoutExpired:
        handle.process.kill()

        returncode = handle.process.wait(
            timeout=timeout,
        )

        return ShutdownResult(
            authorized=True,
            already_stopped=False,
            terminated=True,
            escalated=True,
            returncode=returncode,
            detail=(
                "managed runtime required forced "
                "termination after graceful timeout"
            ),
        )

def inspect_managed_process_orphan(
    record: RuntimeProcessRecord,
    live_process: Optional[subprocess.Popen],
    owner_token: str,
) -> OrphanInspection:
    """Inspect whether managed metadata still maps to its live child."""
    if not can_control_process(
        record,
        owner_token,
    ):
        return OrphanInspection(
            trusted=False,
            orphaned=False,
            running=False,
            pid_matches=False,
            returncode=None,
            detail="runtime ownership proof rejected",
        )

    if live_process is None:
        return OrphanInspection(
            trusted=True,
            orphaned=True,
            running=False,
            pid_matches=False,
            returncode=None,
            detail="managed record has no live process handle",
        )

    current_returncode = live_process.poll()

    if live_process.pid != record.pid:
        return OrphanInspection(
            trusted=True,
            orphaned=True,
            running=(current_returncode is None),
            pid_matches=False,
            returncode=current_returncode,
            detail="managed runtime PID identity no longer matches",
        )

    if current_returncode is not None:
        return OrphanInspection(
            trusted=True,
            orphaned=True,
            running=False,
            pid_matches=True,
            returncode=current_returncode,
            detail="managed runtime child has exited",
        )

    return OrphanInspection(
        trusted=True,
        orphaned=False,
        running=True,
        pid_matches=True,
        returncode=None,
        detail="managed runtime identity is active",
    )
