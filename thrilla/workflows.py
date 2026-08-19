"""Stage 5 background workflow services."""

from dataclasses import dataclass
from typing import Callable, Optional

from .jobs import JobContext, JobManager
from .research import ResearchEngine


class WorkflowError(RuntimeError):
    """A background workflow failed verification."""


@dataclass(frozen=True)
class WorkflowServices:
    jobs: JobManager
    answer_fn: Callable
    research_engine: ResearchEngine
    coding_agent: object
    audit_sink: Optional[Callable] = None

    def _audit(self, event: str, **fields) -> None:
        if self.audit_sink is None:
            return
        try:
            self.audit_sink(event, **fields)
        except TypeError:
            self.audit_sink(event)

    def run_answer_job(self, prompt: str, previous, route: str) -> str:
        def task(ctx: JobContext):
            ctx.checkpoint("answer.reason", next_action="answer.verify")
            answer = self.answer_fn(prompt, previous, route)
            if not str(answer).strip():
                raise WorkflowError("answer workflow returned an empty answer")
            ctx.checkpoint("answer.verify", next_action="finish")
            return str(answer)

        job_id = self.jobs.submit("answer", prompt, task)
        self._audit("answer_job_created", job_id=job_id, route=route)
        return job_id

    def run_research_job(self, query: str) -> str:
        def task(ctx: JobContext):
            result = self.research_engine.research(
                query,
                evidence_target=5,
                job_context=ctx,
            )
            if not result.evidence:
                detail = "; ".join(result.errors) or "no evidence found"
                raise WorkflowError(
                    "research produced no verified evidence: " + detail
                )
            return result

        job_id = self.jobs.submit("research", query, task)
        self._audit("research_job_created", job_id=job_id)
        return job_id

    def run_repair_job(self, goal: str) -> str:
        def task(ctx: JobContext):
            ctx.checkpoint("repair.inspect", next_action="repair.execute")
            outcome = self.coding_agent.run(goal)
            ctx.checkpoint("repair.verify", next_action="finish")
            if not getattr(outcome, "ok", False):
                raise WorkflowError(
                    getattr(outcome, "summary", "repair was not verified")
                )
            return outcome

        job_id = self.jobs.submit("repair", goal, task)
        self._audit("repair_job_created", job_id=job_id)
        return job_id
