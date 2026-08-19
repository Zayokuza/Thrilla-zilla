"""Persistent cooperative background jobs for Thrilla Stage 5."""

import json
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Deque, Dict, Optional, Tuple


class JobError(RuntimeError):
    """Base error for Stage-5 jobs."""


class JobCancelled(JobError):
    """Raised inside a worker when the owner cancels the job."""


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    HELD = "held"
    WAITING = "waiting"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = {
    JobState.COMPLETED,
    JobState.FAILED,
    JobState.CANCELLED,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class JobSnapshot:
    job_id: str
    kind: str
    goal: str
    state: JobState
    priority: int = 0
    current_step: str = ""
    completed_steps: int = 0
    total_steps: Optional[int] = None
    progress: float = 0.0
    started_at: str = ""
    updated_at: str = ""
    elapsed: float = 0.0
    active_workers: int = 0
    evidence_count: int = 0
    last_action: str = ""
    next_action: str = ""
    error: str = ""
    checkpoint: str = ""
    owner_directives: Tuple[str, ...] = ()
    result: object = None
    verified: bool = False


class JobControl:
    """Mutable synchronization state kept separate from snapshots."""

    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.hold_requested = False
        self.cancel_requested = False
        self.directives: Deque[str] = deque()


class JobContext:
    """Cooperative control surface for one worker task."""

    def __init__(
        self,
        manager: "JobManager",
        job_id: str,
        control: JobControl,
    ) -> None:
        self._manager = manager
        self.job_id = job_id
        self._control = control

    def checkpoint(
        self,
        action: str,
        *,
        next_action: str = "",
        completed_steps: Optional[int] = None,
        total_steps: Optional[int] = None,
        progress: Optional[float] = None,
        evidence_count: Optional[int] = None,
    ) -> Tuple[str, ...]:
        self._manager._checkpoint_update(
            self.job_id,
            action=action,
            next_action=next_action,
            completed_steps=completed_steps,
            total_steps=total_steps,
            progress=progress,
            evidence_count=evidence_count,
        )

        with self._control.condition:
            if self._control.cancel_requested:
                raise JobCancelled("job cancelled by owner")

            if self._control.hold_requested:
                self._manager._set_state(
                    self.job_id,
                    JobState.HELD,
                    checkpoint=action,
                    last_action=action,
                    next_action=next_action,
                )
                while (
                    self._control.hold_requested
                    and not self._control.cancel_requested
                ):
                    self._control.condition.wait()

                if self._control.cancel_requested:
                    raise JobCancelled("job cancelled by owner")

                self._manager._set_state(
                    self.job_id,
                    JobState.RUNNING,
                    checkpoint=action,
                    last_action=action,
                    next_action=next_action,
                )

            directives = tuple(self._control.directives)
            self._control.directives.clear()

        if directives:
            self._manager._consume_directives(
                self.job_id,
                len(directives),
            )
        return directives


class JobManager:
    """Bounded worker manager with cached snapshots and atomic persistence."""

    def __init__(
        self,
        state_root: Path,
        max_workers: int = 3,
        audit_sink: Optional[Callable[..., None]] = None,
    ) -> None:
        if int(max_workers) < 1:
            raise ValueError("max_workers must be at least 1")

        self.state_root = Path(state_root)
        self.jobs_root = self.state_root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)

        self.max_workers = int(max_workers)
        self.audit_sink = audit_sink
        self._lock = threading.RLock()
        self._snapshots: Dict[str, JobSnapshot] = {}
        self._controls: Dict[str, JobControl] = {}
        self._started_monotonic: Dict[str, float] = {}
        self._futures = {}
        self._closed = False
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="thrilla-job",
        )

        self._load_persisted()

    def _audit(self, event: str, **fields) -> None:
        if self.audit_sink is None:
            return
        try:
            self.audit_sink(event, **fields)
        except TypeError:
            self.audit_sink(event)

    def _path(self, job_id: str) -> Path:
        return self.jobs_root / f"{job_id}.json"

    def _payload(self, snapshot: JobSnapshot) -> dict:
        payload = asdict(snapshot)
        payload["state"] = snapshot.state.value
        payload["owner_directives"] = list(snapshot.owner_directives)
        try:
            json.dumps(payload["result"])
        except (TypeError, ValueError):
            payload["result"] = str(payload["result"])
        return payload

    def _persist(self, snapshot: JobSnapshot) -> None:
        path = self._path(snapshot.job_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                self._payload(snapshot),
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def _load_persisted(self) -> None:
        for path in sorted(self.jobs_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                state = JobState(payload["state"])
                if state in {
                    JobState.QUEUED,
                    JobState.RUNNING,
                    JobState.VERIFYING,
                }:
                    state = JobState.WAITING
                    payload["verified"] = False
                    payload["result"] = None

                snapshot = JobSnapshot(
                    job_id=str(payload["job_id"]),
                    kind=str(payload.get("kind", "")),
                    goal=str(payload.get("goal", "")),
                    state=state,
                    priority=int(payload.get("priority", 0)),
                    current_step=str(payload.get("current_step", "")),
                    completed_steps=int(payload.get("completed_steps", 0)),
                    total_steps=payload.get("total_steps"),
                    progress=float(payload.get("progress", 0.0)),
                    started_at=str(payload.get("started_at", "")),
                    updated_at=str(payload.get("updated_at", "")),
                    elapsed=float(payload.get("elapsed", 0.0)),
                    active_workers=0,
                    evidence_count=int(payload.get("evidence_count", 0)),
                    last_action=str(payload.get("last_action", "")),
                    next_action=str(payload.get("next_action", "")),
                    error=str(payload.get("error", "")),
                    checkpoint=str(payload.get("checkpoint", "")),
                    owner_directives=tuple(
                        payload.get("owner_directives", ())
                    ),
                    result=payload.get("result"),
                    verified=bool(payload.get("verified", False)),
                )
            except (
                OSError,
                ValueError,
                TypeError,
                KeyError,
                json.JSONDecodeError,
            ):
                continue

            self._snapshots[snapshot.job_id] = snapshot
            self._controls[snapshot.job_id] = JobControl()
            if snapshot.state in {JobState.WAITING, JobState.HELD}:
                self._persist(snapshot)

    def _elapsed_for(self, job_id: str, prior: float) -> float:
        started = self._started_monotonic.get(job_id)
        if started is None:
            return prior
        return max(prior, time.monotonic() - started)

    def _replace_snapshot(self, job_id: str, **changes) -> JobSnapshot:
        with self._lock:
            current = self._snapshots[job_id]
            changes.setdefault(
                "elapsed",
                self._elapsed_for(job_id, current.elapsed),
            )
            changes.setdefault("updated_at", _utc_now())
            snapshot = replace(current, **changes)
            self._snapshots[job_id] = snapshot
            self._persist(snapshot)
            return snapshot

    def _set_state(
        self,
        job_id: str,
        state: JobState,
        **changes,
    ) -> JobSnapshot:
        changes["state"] = state
        if state in _TERMINAL_STATES:
            changes["active_workers"] = 0
        return self._replace_snapshot(job_id, **changes)

    def _checkpoint_update(
        self,
        job_id: str,
        *,
        action: str,
        next_action: str,
        completed_steps: Optional[int],
        total_steps: Optional[int],
        progress: Optional[float],
        evidence_count: Optional[int],
    ) -> JobSnapshot:
        changes = {
            "current_step": str(action),
            "last_action": str(action),
            "next_action": str(next_action),
            "checkpoint": str(action),
        }
        if completed_steps is not None:
            changes["completed_steps"] = int(completed_steps)
        if total_steps is not None:
            changes["total_steps"] = int(total_steps)
        if progress is not None:
            changes["progress"] = max(
                0.0,
                min(1.0, float(progress)),
            )
        if evidence_count is not None:
            changes["evidence_count"] = max(
                0,
                int(evidence_count),
            )
        return self._replace_snapshot(job_id, **changes)

    def _consume_directives(self, job_id: str, count: int) -> None:
        with self._lock:
            current = self._snapshots[job_id]
            self._replace_snapshot(
                job_id,
                owner_directives=current.owner_directives[count:],
            )

    def submit(
        self,
        kind: str,
        goal: str,
        task: Callable[[JobContext], object],
        priority: int = 0,
    ) -> str:
        if self._closed:
            raise JobError("job manager is shut down")
        if not callable(task):
            raise TypeError("task must be callable")

        job_id = uuid.uuid4().hex
        now = _utc_now()
        snapshot = JobSnapshot(
            job_id=job_id,
            kind=str(kind),
            goal=str(goal),
            state=JobState.QUEUED,
            priority=int(priority),
            started_at=now,
            updated_at=now,
        )
        control = JobControl()

        with self._lock:
            self._snapshots[job_id] = snapshot
            self._controls[job_id] = control
            self._persist(snapshot)

        self._audit("job_created", job_id=job_id, kind=str(kind))
        future = self._executor.submit(
            self._run_task,
            job_id,
            task,
            control,
        )
        with self._lock:
            self._futures[job_id] = future
        return job_id

    def _run_task(
        self,
        job_id: str,
        task: Callable[[JobContext], object],
        control: JobControl,
    ) -> None:
        self._started_monotonic[job_id] = time.monotonic()
        self._set_state(
            job_id,
            JobState.RUNNING,
            active_workers=1,
        )
        self._audit("job_started", job_id=job_id)
        context = JobContext(self, job_id, control)

        try:
            with control.condition:
                if control.cancel_requested:
                    raise JobCancelled("job cancelled by owner")

            result = task(context)

            with control.condition:
                if control.cancel_requested:
                    raise JobCancelled("job cancelled by owner")

            self._set_state(
                job_id,
                JobState.VERIFYING,
                result=result,
                verified=False,
            )
            self._set_state(
                job_id,
                JobState.COMPLETED,
                result=result,
                verified=True,
                error="",
                progress=1.0,
            )
            self._audit("job_completed", job_id=job_id)
        except JobCancelled as error:
            self._set_state(
                job_id,
                JobState.CANCELLED,
                result=None,
                verified=False,
                error=str(error),
            )
            self._audit("job_cancelled", job_id=job_id)
        except Exception as error:
            self._set_state(
                job_id,
                JobState.FAILED,
                result=None,
                verified=False,
                error=f"{type(error).__name__}: {error}",
            )
            self._audit(
                "job_failed",
                job_id=job_id,
                error=type(error).__name__,
            )

    def snapshot(self, job_id: str) -> JobSnapshot:
        with self._lock:
            try:
                current = self._snapshots[job_id]
            except KeyError as error:
                raise KeyError(
                    f"unknown job: {job_id}"
                ) from error

            if current.state not in _TERMINAL_STATES:
                elapsed = self._elapsed_for(
                    job_id,
                    current.elapsed,
                )
                if elapsed != current.elapsed:
                    current = replace(
                        current,
                        elapsed=elapsed,
                    )
                    self._snapshots[job_id] = current
            return current

    def hold(self, job_id: str) -> JobSnapshot:
        with self._lock:
            control = self._controls[job_id]
            snapshot = self._snapshots[job_id]

        if snapshot.state in _TERMINAL_STATES:
            return snapshot

        with control.condition:
            control.hold_requested = True
            control.condition.notify_all()

        self._audit("job_hold_requested", job_id=job_id)
        return self.snapshot(job_id)

    def resume(self, job_id: str) -> JobSnapshot:
        with self._lock:
            control = self._controls[job_id]
            snapshot = self._snapshots[job_id]

        if snapshot.state in _TERMINAL_STATES:
            return snapshot

        with control.condition:
            control.hold_requested = False
            control.condition.notify_all()

        self._audit("job_resumed", job_id=job_id)
        return self.snapshot(job_id)

    def directive(self, job_id: str, text: str) -> JobSnapshot:
        value = str(text).strip()
        if not value:
            raise ValueError("directive must not be empty")

        with self._lock:
            control = self._controls[job_id]
            current = self._snapshots[job_id]

        if current.state in _TERMINAL_STATES:
            raise JobError("cannot direct a terminal job")

        with control.condition:
            control.directives.append(value)

        snapshot = self._replace_snapshot(
            job_id,
            owner_directives=current.owner_directives + (value,),
        )
        self._audit("job_directive_received", job_id=job_id)
        return snapshot

    def cancel(self, job_id: str) -> JobSnapshot:
        with self._lock:
            control = self._controls[job_id]
            current = self._snapshots[job_id]

        if current.state in _TERMINAL_STATES:
            return current

        with control.condition:
            control.cancel_requested = True
            control.hold_requested = False
            control.condition.notify_all()

        snapshot = self._set_state(
            job_id,
            JobState.CANCELLED,
            result=None,
            verified=False,
            error="job cancelled by owner",
        )
        self._audit("job_cancel_requested", job_id=job_id)
        return snapshot

    def wait(
        self,
        job_id: str,
        timeout: Optional[float] = None,
    ) -> JobSnapshot:
        with self._lock:
            future = self._futures.get(job_id)

        if future is not None:
            try:
                future.result(timeout=timeout)
            except FutureTimeout:
                return self.snapshot(job_id)
            except Exception:
                pass

        return self.snapshot(job_id)

    def recoverable(self) -> Tuple[JobSnapshot, ...]:
        with self._lock:
            return tuple(
                self._snapshots[job_id]
                for job_id in sorted(self._snapshots)
                if self._snapshots[job_id].state is JobState.WAITING
            )

    def shutdown(self, wait: bool = False) -> None:
        self._closed = True
        self._executor.shutdown(wait=bool(wait))

