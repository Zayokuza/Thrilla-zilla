"""Stage 5 RED tests for persisted job restart recovery."""

import tempfile
import threading
import time
import unittest
from pathlib import Path

_IMPORT_ERROR = None

try:
    from thrilla.jobs import JobManager, JobState
except ModuleNotFoundError as error:
    if getattr(error, "name", "") != "thrilla.jobs":
        raise
    _IMPORT_ERROR = error
    JobManager = None
    JobState = None


def wait_for_state(manager, job_id, state, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = manager.snapshot(job_id)
        if snapshot.state is state:
            return snapshot
        time.sleep(0.01)
    return manager.snapshot(job_id)


@unittest.skipIf(_IMPORT_ERROR is not None, "Stage 5 jobs module not implemented yet")
class JobRecoveryTests(unittest.TestCase):
    def test_restart_converts_running_job_to_waiting_not_completed(self):
        with tempfile.TemporaryDirectory() as root:
            state_root = Path(root)
            release = threading.Event()
            started = threading.Event()

            first = JobManager(state_root, max_workers=1)

            def task(ctx):
                ctx.checkpoint("working", next_action="later")
                started.set()
                self.assertTrue(release.wait(2.0))
                ctx.checkpoint("later")
                return "done"

            job_id = first.submit("test", "goal", task)
            self.assertTrue(started.wait(1.0))
            self.assertIs(first.snapshot(job_id).state, JobState.RUNNING)

            restarted = JobManager(state_root, max_workers=1)
            try:
                recovered = restarted.snapshot(job_id)
                self.assertIs(recovered.state, JobState.WAITING)
                self.assertFalse(recovered.verified)
                self.assertIsNone(recovered.result)
                self.assertEqual(
                    tuple(item.job_id for item in restarted.recoverable()),
                    (job_id,),
                )
            finally:
                release.set()
                first.wait(job_id, timeout=2.0)
                first.shutdown(True)
                restarted.shutdown(True)

    def test_restart_preserves_held_job_as_held(self):
        with tempfile.TemporaryDirectory() as root:
            state_root = Path(root)
            reached_first = threading.Event()
            allow_hold_checkpoint = threading.Event()

            first = JobManager(state_root, max_workers=1)

            def task(ctx):
                ctx.checkpoint("first", next_action="second")
                reached_first.set()
                self.assertTrue(allow_hold_checkpoint.wait(2.0))
                ctx.checkpoint("second")
                return "done"

            job_id = first.submit("test", "goal", task)
            self.assertTrue(reached_first.wait(1.0))
            first.hold(job_id)
            allow_hold_checkpoint.set()

            held = wait_for_state(first, job_id, JobState.HELD)
            self.assertIs(held.state, JobState.HELD)

            restarted = JobManager(state_root, max_workers=1)
            try:
                recovered = restarted.snapshot(job_id)
                self.assertIs(recovered.state, JobState.HELD)
                self.assertFalse(recovered.verified)
            finally:
                first.cancel(job_id)
                first.resume(job_id)
                first.wait(job_id, timeout=2.0)
                first.shutdown(True)
                restarted.shutdown(True)

    def test_restart_preserves_terminal_states(self):
        with tempfile.TemporaryDirectory() as root:
            state_root = Path(root)
            first = JobManager(state_root, max_workers=2)

            complete_id = first.submit(
                "test",
                "complete",
                lambda ctx: "done",
            )

            def fail(ctx):
                raise ValueError("failed")

            fail_id = first.submit("test", "fail", fail)

            completed = first.wait(complete_id, timeout=2.0)
            failed = first.wait(fail_id, timeout=2.0)

            self.assertIs(completed.state, JobState.COMPLETED)
            self.assertIs(failed.state, JobState.FAILED)

            first.shutdown(True)

            restarted = JobManager(state_root, max_workers=1)
            try:
                self.assertIs(
                    restarted.snapshot(complete_id).state,
                    JobState.COMPLETED,
                )
                self.assertIs(
                    restarted.snapshot(fail_id).state,
                    JobState.FAILED,
                )
                self.assertEqual(restarted.recoverable(), ())
            finally:
                restarted.shutdown(True)


if __name__ == "__main__":
    unittest.main()

