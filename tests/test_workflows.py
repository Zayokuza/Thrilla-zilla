"""Stage 5 Task 5 workflow-service tests."""

import tempfile
import threading
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from thrilla.jobs import JobManager, JobState
from thrilla.research import ResearchEvidence, ResearchResult
from thrilla.workflows import WorkflowServices


class FakeResearch:
    def research(self, query, evidence_target=5, job_context=None):
        if job_context is not None:
            job_context.checkpoint("research.fake", next_action="finish")
        return ResearchResult(
            query=query,
            evidence=(
                ResearchEvidence(
                    url="https://example.com",
                    title="Example",
                    text="verified evidence",
                    digest="abc",
                ),
            ),
            errors=(),
        )


@dataclass
class RepairOutcome:
    ok: bool
    summary: str = "repair result"


class FakeCoding:
    def __init__(self, ok=True):
        self.ok = ok

    def run(self, goal):
        return RepairOutcome(self.ok)


class WorkflowServicesTests(unittest.TestCase):
    def make_services(self, answer_fn=None, coding_ok=True):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        jobs = JobManager(Path(temp.name), max_workers=3)
        self.addCleanup(jobs.shutdown, True)
        return WorkflowServices(
            jobs=jobs,
            answer_fn=answer_fn or (
                lambda prompt, previous, route: "answer"
            ),
            research_engine=FakeResearch(),
            coding_agent=FakeCoding(coding_ok),
        )

    def test_answer_runs_as_background_job(self):
        services = self.make_services()
        job_id = services.run_answer_job("hello", [], "general-chat")
        snapshot = services.jobs.wait(job_id, timeout=2.0)
        self.assertIs(snapshot.state, JobState.COMPLETED)
        self.assertEqual(snapshot.result, "answer")
        self.assertTrue(snapshot.verified)

    def test_research_runs_as_background_job(self):
        services = self.make_services()
        job_id = services.run_research_job("query")
        snapshot = services.jobs.wait(job_id, timeout=2.0)
        self.assertIs(snapshot.state, JobState.COMPLETED)
        self.assertEqual(len(snapshot.result.evidence), 1)

    def test_unverified_repair_is_not_claimed_complete(self):
        services = self.make_services(coding_ok=False)
        job_id = services.run_repair_job("fix it")
        snapshot = services.jobs.wait(job_id, timeout=2.0)
        self.assertIs(snapshot.state, JobState.FAILED)
        self.assertFalse(snapshot.verified)

    def test_blocked_answer_worker_does_not_block_job_control(self):
        started = threading.Event()
        release = threading.Event()

        def blocked(prompt, previous, route):
            started.set()
            release.wait(2.0)
            return "done"

        services = self.make_services(answer_fn=blocked)
        job_id = services.run_answer_job("wait", [], "general-chat")
        self.assertTrue(started.wait(1.0))

        before = time.perf_counter()
        snapshot = services.jobs.snapshot(job_id)
        services.jobs.hold(job_id)
        elapsed = time.perf_counter() - before

        self.assertIn(snapshot.state, {JobState.RUNNING, JobState.HELD})
        self.assertLess(elapsed, 0.1)
        release.set()
        services.jobs.resume(job_id)
        services.jobs.wait(job_id, timeout=2.0)


if __name__ == "__main__":
    unittest.main()
