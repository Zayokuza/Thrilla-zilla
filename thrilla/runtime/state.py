"""Runtime lifecycle state definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List


class RuntimeState(str, Enum):
    """Observable lifecycle states for a local model runtime."""

    UNKNOWN = "unknown"
    STOPPED = "stopped"
    DISCOVERING = "discovering"
    SELECTING = "selecting"
    STARTING = "starting"
    LOADING_MODEL = "loading_model"
    HEALTH_CHECKING = "health_checking"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    FAILED = "failed"
    CRASHED = "crashed"
    RECOVERING = "recovering"


@dataclass(frozen=True)
class StateTransition:
    """One observable runtime lifecycle transition."""

    previous: RuntimeState
    next: RuntimeState
    timestamp: str
    actor: str
    reason: str
    model: str
    pid: int
    elapsed: float
    result: str


class RuntimeStateMachine:
    """Tracks the current runtime state and its transition history."""

    def __init__(
        self,
        initial: RuntimeState = RuntimeState.UNKNOWN,
    ) -> None:
        self.current = initial
        self.history: List[StateTransition] = []

    def transition(
        self,
        next_state: RuntimeState,
        *,
        actor: str,
        reason: str,
        model: str,
        pid: int,
        elapsed: float,
        result: str,
    ) -> StateTransition:
        allowed = {
            RuntimeState.UNKNOWN: {
                RuntimeState.DISCOVERING,
            },
            RuntimeState.DISCOVERING: {
                RuntimeState.SELECTING,
            },
            RuntimeState.SELECTING: {
                RuntimeState.STARTING,
            },
            RuntimeState.STOPPED: {
                RuntimeState.STARTING,
            },
            RuntimeState.STARTING: {
                RuntimeState.LOADING_MODEL,
                RuntimeState.FAILED,
            },
            RuntimeState.LOADING_MODEL: {
                RuntimeState.HEALTH_CHECKING,
                RuntimeState.FAILED,
            },
            RuntimeState.HEALTH_CHECKING: {
                RuntimeState.READY,
                RuntimeState.FAILED,
            },
            RuntimeState.READY: {
                RuntimeState.BUSY,
                RuntimeState.STOPPING,
            },
            RuntimeState.BUSY: {
                RuntimeState.READY,
            },
            RuntimeState.STOPPING: {
                RuntimeState.STOPPED,
            },
            RuntimeState.CRASHED: {
                RuntimeState.RECOVERING,
            },
            RuntimeState.RECOVERING: {
                RuntimeState.STARTING,
            },
        }

        if next_state not in allowed.get(self.current, set()):
            raise ValueError(
                "Illegal runtime transition: {0} -> {1}".format(
                    self.current.name,
                    next_state.name,
                )
            )

        transition = StateTransition(
            previous=self.current,
            next=next_state,
            timestamp=datetime.now().astimezone().isoformat(),
            actor=actor,
            reason=reason,
            model=model,
            pid=pid,
            elapsed=elapsed,
            result=result,
        )

        self.current = next_state
        self.history.append(transition)
        return transition

