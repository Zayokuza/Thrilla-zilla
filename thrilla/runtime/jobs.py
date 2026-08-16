"""Small non-blocking runtime job boundary."""

from dataclasses import dataclass
from enum import Enum
from threading import Lock, Thread
from typing import Callable, Optional


class RuntimeJobState(Enum):
    """Lifecycle state for one background runtime job."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeJobSnapshot:
    """Immutable observation of the current runtime job."""

    state: RuntimeJobState
    result: object = None
    error: str = ""


class RuntimeJob:
    """Run at most one background worker at a time."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = RuntimeJobState.IDLE
        self._result = None
        self._error = ""
        self._thread = None  # type: Optional[Thread]

    def start(
        self,
        worker: Callable[[], object],
    ) -> None:
        """Start worker without blocking the caller."""
        with self._lock:
            if self._state == RuntimeJobState.RUNNING:
                raise RuntimeError(
                    "runtime job is already running"
                )

            self._state = RuntimeJobState.RUNNING
            self._result = None
            self._error = ""

            thread = Thread(
                target=self._run,
                args=(worker,),
                daemon=True,
            )
            self._thread = thread

        thread.start()

    def _run(
        self,
        worker: Callable[[], object],
    ) -> None:
        try:
            result = worker()
        except Exception as error:
            with self._lock:
                self._state = RuntimeJobState.FAILED
                self._result = None
                self._error = str(error)
            return

        with self._lock:
            self._state = RuntimeJobState.SUCCEEDED
            self._result = result
            self._error = ""

    def snapshot(self) -> RuntimeJobSnapshot:
        """Return the current retained job state."""
        with self._lock:
            return RuntimeJobSnapshot(
                state=self._state,
                result=self._result,
                error=self._error,
            )

    def wait(
        self,
        timeout: Optional[float] = None,
    ) -> RuntimeJobSnapshot:
        """Wait up to timeout for the active worker."""
        with self._lock:
            thread = self._thread

        if thread is not None:
            thread.join(timeout)

        return self.snapshot()
