import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from thrilla.jobs import (
    JobManager,
    JobState,
)
from thrilla.workflows import (
    WorkflowServices,
)


class FakeResearch:
    pass


class FakeCoding:
    pass


class FakeAutonomy:
    def __init__(self):
        self.calls = []

    def run(
        self,
        goal,
        job_context=None,
    ):
        self.calls.append(
            (
                goal,
                job_context,
            )
        )

        if job_context is not None:
            job_context.checkpoint(
                "autonomy.fake",
                next_action="finish",
                completed_steps=1,
                total_steps=1,
                evidence_count=1,
            )

        return SimpleNamespace(
            completed=True,
            answer="autonomous result",
            steps=(),
            tool_calls=1,
            evidence_count=1,
        )


class Stage7CWorkflowTests(unittest.TestCase):
    def test_autonomous_task_runs_as_background_job(self):
        with tempfile.TemporaryDirectory() as root:
            jobs = JobManager(
                Path(root),
                max_workers=2,
            )

            self.addCleanup(
                jobs.shutdown,
                True,
            )

            autonomy = FakeAutonomy()

            services = WorkflowServices(
                jobs=jobs,
                answer_fn=lambda *args: "answer",
                research_engine=FakeResearch(),
                coding_agent=FakeCoding(),
                autonomous_runner=autonomy,
            )

            job_id = (
                services.run_autonomous_job(
                    "inspect repository"
                )
            )

            snapshot = jobs.wait(
                job_id,
                timeout=2.0,
            )

            self.assertIs(
                snapshot.state,
                JobState.COMPLETED,
            )

            self.assertTrue(
                snapshot.verified
            )

            self.assertEqual(
                snapshot.kind,
                "autonomous",
            )

            self.assertEqual(
                snapshot.result.answer,
                "autonomous result",
            )

            self.assertEqual(
                autonomy.calls[0][0],
                "inspect repository",
            )


if __name__ == "__main__":
    unittest.main()
