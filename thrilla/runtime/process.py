"""Runtime process ownership metadata."""

import hmac
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


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
