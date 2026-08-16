import importlib
import threading
import time
import unittest


class RuntimeJobTests(unittest.TestCase):

    def _jobs_module(self):
        try:
            return importlib.import_module(
                "thrilla.runtime.jobs"
            )
        except Exception as error:
            self.fail(
                "runtime jobs module must exist: {0}".format(
                    error
                )
            )

    def test_start_returns_without_waiting_for_worker(self):
        jobs = self._jobs_module()

        job = jobs.RuntimeJob()
        release = threading.Event()

        def worker():
            release.wait(2.0)
            return "ready"

        timer = threading.Timer(
            0.6,
            release.set,
        )
        timer.start()

        started_at = time.monotonic()
        job.start(worker)
        elapsed = time.monotonic() - started_at

        release.set()
        timer.cancel()
        job.wait(1.0)

        self.assertLess(
            elapsed,
            0.3,
            "starting a runtime job must not wait for the worker",
        )

    def test_second_active_start_is_rejected(self):
        jobs = self._jobs_module()

        job = jobs.RuntimeJob()
        entered = threading.Event()
        release = threading.Event()

        def worker():
            entered.set()
            release.wait(2.0)
            return "first"

        job.start(worker)

        self.assertTrue(
            entered.wait(1.0),
            "first worker did not start",
        )

        try:
            with self.assertRaises(RuntimeError):
                job.start(lambda: "second")
        finally:
            release.set()
            job.wait(1.0)

    def test_successful_result_is_retained(self):
        jobs = self._jobs_module()

        job = jobs.RuntimeJob()

        job.start(lambda: "runtime-ready")
        snapshot = job.wait(1.0)

        self.assertEqual(
            jobs.RuntimeJobState.SUCCEEDED,
            snapshot.state,
        )
        self.assertEqual(
            "runtime-ready",
            snapshot.result,
        )
        self.assertEqual(
            "",
            snapshot.error,
        )

        retained = job.snapshot()

        self.assertEqual(
            jobs.RuntimeJobState.SUCCEEDED,
            retained.state,
        )
        self.assertEqual(
            "runtime-ready",
            retained.result,
        )

    def test_worker_failure_is_retained_as_failed_state(self):
        jobs = self._jobs_module()

        job = jobs.RuntimeJob()

        def worker():
            raise ValueError("runtime load exploded")

        job.start(worker)
        snapshot = job.wait(1.0)

        self.assertEqual(
            jobs.RuntimeJobState.FAILED,
            snapshot.state,
        )
        self.assertIsNone(snapshot.result)
        self.assertIn(
            "runtime load exploded",
            snapshot.error,
        )

        retained = job.snapshot()

        self.assertEqual(
            jobs.RuntimeJobState.FAILED,
            retained.state,
        )
        self.assertIn(
            "runtime load exploded",
            retained.error,
        )


if __name__ == "__main__":
    unittest.main()
