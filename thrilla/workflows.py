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
    autonomous_runner: object = None

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
            try:
                answer = self.answer_fn(prompt, previous, route)
            except Exception as error:
                self._audit(
                    "model_request_failed",
                    route=route,
                    prompt_chars=len(prompt),
                    error=type(error).__name__,
                )
                raise

            if not str(answer).strip():
                error = WorkflowError(
                    "answer workflow returned an empty answer"
                )
                self._audit(
                    "model_request_failed",
                    route=route,
                    prompt_chars=len(prompt),
                    error=type(error).__name__,
                )
                raise error

            ctx.checkpoint("answer.verify", next_action="finish")
            answer = str(answer)
            self._audit(
                "model_request_completed",
                route=route,
                prompt_chars=len(prompt),
                answer_chars=len(answer),
            )
            return answer

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

    def run_autonomous_job(self, goal: str) -> str:
        if self.autonomous_runner is None:
            raise WorkflowError(
                "autonomous runner is not configured"
            )

        def task(ctx: JobContext):
            ctx.checkpoint(
                "autonomy.start",
                next_action="autonomy.plan.1",
                completed_steps=0,
                evidence_count=0,
            )

            outcome = self.autonomous_runner.run(
                goal,
                job_context=ctx,
            )

            if not getattr(
                outcome,
                "completed",
                False,
            ):
                raise WorkflowError(
                    "autonomous workflow did not complete"
                )

            answer = str(
                getattr(
                    outcome,
                    "answer",
                    "",
                )
            ).strip()

            if not answer:
                raise WorkflowError(
                    "autonomous workflow returned no answer"
                )

            self._audit(
                "autonomous_job_completed",
                tool_calls=int(
                    getattr(
                        outcome,
                        "tool_calls",
                        0,
                    )
                ),
                evidence_count=int(
                    getattr(
                        outcome,
                        "evidence_count",
                        0,
                    )
                ),
                replans=int(
                    getattr(
                        outcome,
                        "replans",
                        0,
                    )
                ),
                tool_failures=int(
                    getattr(
                        outcome,
                        "tool_failures",
                        0,
                    )
                ),
                protocol_errors=int(
                    getattr(
                        outcome,
                        "protocol_errors",
                        0,
                    )
                ),
                critic_checks=int(
                    getattr(
                        outcome,
                        "critic_checks",
                        0,
                    )
                ),
                loop_blocks=int(
                    getattr(
                        outcome,
                        "loop_blocks",
                        0,
                    )
                ),
            )

            return outcome

        job_id = self.jobs.submit(
            "autonomous",
            goal,
            task,
        )

        self._audit(
            "autonomous_job_created",
            job_id=job_id,
        )

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
