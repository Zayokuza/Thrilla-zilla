"""Stage 5 RED tests for persistent cooperative background jobs."""

import dataclasses
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


class Stage5JobsModuleRedTest(unittest.TestCase):
    def test_jobs_module_exists(self):
        self.assertIsNone(
            _IMPORT_ERROR,
            "Stage 5 jobs module not implemented yet",
        )


@unittest.skipIf(_IMPORT_ERROR is not None, "Stage 5 jobs module not implemented yet")
class JobManagerBehaviorTests(unittest.TestCase):
    def make_manager(self, max_workers=2):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        manager = JobManager(Path(temp.name), max_workers=max_workers)
        self.addCleanup(manager.shutdown, True)
        return manager, Path(temp.name)

    def test_successful_task_reaches_verified_completed_state(self):
        manager, _ = self.make_manager(max_workers=1)

        def task(ctx):
            ctx.checkpoint("work", next_action="verify")
            return "answer"

        job_id = manager.submit("test", "goal", task)
        snapshot = manager.wait(job_id, timeout=2.0)

        self.assertIs(snapshot.state, JobState.COMPLETED)
        self.assertEqual(snapshot.result, "answer")
        self.assertEqual(snapshot.error, "")
        self.assertTrue(snapshot.verified)

    def test_task_exception_fails_without_claiming_completion(self):
        manager, _ = self.make_manager(max_workers=1)

        def task(ctx):
            ctx.checkpoint("explode")
            raise RuntimeError("boom")

        job_id = manager.submit("test", "goal", task)
        snapshot = manager.wait(job_id, timeout=2.0)

        self.assertIs(snapshot.state, JobState.FAILED)
        self.assertFalse(snapshot.verified)
        self.assertEqual(snapshot.result, None)
        self.assertIn("RuntimeError", snapshot.error)
        self.assertIn("boom", snapshot.error)

    def test_hold_blocks_the_next_checkpoint_until_explicit_resume(self):
        manager, _ = self.make_manager(max_workers=1)
        reached_first = threading.Event()
        allow_second = threading.Event()
        passed_second = threading.Event()

        def task(ctx):
            ctx.checkpoint("first", next_action="second")
            reached_first.set()
            self.assertTrue(allow_second.wait(2.0))
            ctx.checkpoint("second", next_action="finish")
            passed_second.set()
            return "done"

        job_id = manager.submit("test", "goal", task)
        self.assertTrue(reached_first.wait(1.0))

        manager.hold(job_id)
        allow_second.set()

        held = wait_for_state(manager, job_id, JobState.HELD)
        self.assertIs(held.state, JobState.HELD)
        self.assertFalse(passed_second.is_set())

        manager.resume(job_id)

        self.assertTrue(passed_second.wait(1.0))
        completed = manager.wait(job_id, timeout=2.0)
        self.assertIs(completed.state, JobState.COMPLETED)

    def test_directive_is_delivered_at_checkpoint_without_changing_run_state(self):
        manager, _ = self.make_manager(max_workers=1)
        waiting = threading.Event()
        release = threading.Event()
        received = []

        def task(ctx):
            ctx.checkpoint("first")
            waiting.set()
            self.assertTrue(release.wait(2.0))
            received.extend(ctx.checkpoint("second"))
            return "done"

        job_id = manager.submit("test", "goal", task)
        self.assertTrue(waiting.wait(1.0))

        before = manager.snapshot(job_id).state
        after_directive = manager.directive(
            job_id,
            "prioritize speed",
        )

        self.assertIs(after_directive.state, before)

        release.set()
        completed = manager.wait(job_id, timeout=2.0)

        self.assertIs(completed.state, JobState.COMPLETED)
        self.assertEqual(received, ["prioritize speed"])

    def test_cancelled_job_never_completes(self):
        manager, _ = self.make_manager(max_workers=1)
        waiting = threading.Event()
        release = threading.Event()

        def task(ctx):
            ctx.checkpoint("first")
            waiting.set()
            self.assertTrue(release.wait(2.0))
            ctx.checkpoint("second")
            return "must-not-complete"

        job_id = manager.submit("test", "goal", task)
        self.assertTrue(waiting.wait(1.0))

        manager.cancel(job_id)
        release.set()

        snapshot = manager.wait(job_id, timeout=2.0)
        self.assertIs(snapshot.state, JobState.CANCELLED)
        self.assertFalse(snapshot.verified)
        self.assertNotEqual(snapshot.result, "must-not-complete")

    def test_snapshot_is_immutable_and_memory_backed(self):
        manager, state_root = self.make_manager(max_workers=1)

        job_id = manager.submit(
            "test",
            "goal",
            lambda ctx: "done",
        )
        snapshot = manager.wait(job_id, timeout=2.0)

        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.state = JobState.FAILED

        persisted = state_root / "jobs" / f"{job_id}.json"
        self.assertTrue(persisted.is_file())
        persisted.unlink()

        cached = manager.snapshot(job_id)
        self.assertIs(cached.state, JobState.COMPLETED)
        self.assertEqual(cached.result, "done")


if __name__ == "__main__":
    unittest.main()

