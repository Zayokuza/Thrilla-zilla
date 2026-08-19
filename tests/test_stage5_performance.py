"""Stage 5 final performance and responsiveness gates."""

import statistics
import tempfile
import threading
import time
import unittest
from pathlib import Path

from thrilla.jobs import JobManager, JobState


def p95(samples):
    ordered = sorted(samples)
    index = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[index]


class Stage5PerformanceTests(unittest.TestCase):
    def make_manager(self, workers=2):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        manager = JobManager(Path(temp.name), max_workers=workers)
        self.addCleanup(manager.shutdown, True)
        return manager

    def test_snapshot_p95_under_five_ms(self):
        manager = self.make_manager()
        job_id = manager.submit("test", "done", lambda ctx: "ok")
        completed = manager.wait(job_id, timeout=2.0)
        self.assertIs(completed.state, JobState.COMPLETED)

        samples = []
        for _ in range(1000):
            started = time.perf_counter()
            manager.snapshot(job_id)
            samples.append(time.perf_counter() - started)

        self.assertLess(
            p95(samples),
            0.005,
            "job snapshot p95 must stay below 5 ms",
        )

    def test_control_mutation_p95_under_ten_ms(self):
        manager = self.make_manager()
        started_event = threading.Event()
        release = threading.Event()

        def task(ctx):
            ctx.checkpoint("started")
            started_event.set()
            release.wait(3.0)
            ctx.checkpoint("finish")
            return "ok"

        job_id = manager.submit("test", "control", task)
        self.assertTrue(started_event.wait(1.0))

        samples = []
        for _ in range(100):
            began = time.perf_counter()
            manager.hold(job_id)
            manager.resume(job_id)
            samples.append(time.perf_counter() - began)

        release.set()
        manager.wait(job_id, timeout=2.0)

        self.assertLess(
            p95(samples),
            0.010,
            "hold/resume mutation p95 must stay below 10 ms",
        )

    def test_blocked_worker_does_not_block_foreground_snapshot(self):
        manager = self.make_manager(workers=1)
        started_event = threading.Event()
        release = threading.Event()

        def task(ctx):
            ctx.checkpoint("blocked")
            started_event.set()
            release.wait(3.0)
            return "ok"

        job_id = manager.submit("answer", "blocked", task)
        self.assertTrue(started_event.wait(1.0))

        began = time.perf_counter()
        snapshot = manager.snapshot(job_id)
        elapsed = time.perf_counter() - began

        self.assertIn(snapshot.state, {JobState.RUNNING, JobState.HELD})
        self.assertLess(elapsed, 0.050)

        release.set()
        manager.wait(job_id, timeout=2.0)


if __name__ == "__main__":
    unittest.main()
