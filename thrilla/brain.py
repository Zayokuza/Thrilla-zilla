"""Deterministic autonomous control loop for Thrilla goals."""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple


class BrainError(RuntimeError):
    """Raised when an autonomous run cannot produce a verified result."""


@dataclass(frozen=True)
class BrainEvent:
    """One observable phase transition in an autonomous run."""

    phase: str
    attempt: int
    detail: str


@dataclass(frozen=True)
class BrainResult:
    """Verified result from one autonomous brain run."""

    answer: str
    verified: bool
    attempts: int
    events: Tuple[BrainEvent, ...]


class AgentBrain:
    """Observe, plan, act, verify and replan until a result is verified."""

    def __init__(
        self,
        max_attempts: int = 2,
        event_sink: Optional[Callable[[BrainEvent], None]] = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self.event_sink = event_sink

    def _event(self, events, phase: str, attempt: int, detail: str) -> None:
        event = BrainEvent(phase=phase, attempt=attempt, detail=detail)
        events.append(event)
        if self.event_sink is not None:
            self.event_sink(event)

    def run(
        self,
        goal: str,
        observe: Callable[[str], Any],
        plan: Callable[[str, Any, int], Any],
        act: Callable[[Any, int], Any],
        verify: Callable[[str, Any, Any], bool],
    ) -> BrainResult:
        """Run one bounded autonomous loop and require verified completion."""
        events = []
        observation = observe(goal)
        self._event(events, "OBSERVE", 0, "goal context observed")

        for attempt in range(1, self.max_attempts + 1):
            action_plan = plan(goal, observation, attempt)
            self._event(events, "PLAN", attempt, "action plan selected")

            outcome = act(action_plan, attempt)
            self._event(events, "ACT", attempt, "planned action executed")

            verified = bool(verify(goal, outcome, observation))
            self._event(
                events,
                "VERIFY",
                attempt,
                "outcome verified" if verified else "outcome rejected; replanning",
            )

            if verified:
                answer = outcome if isinstance(outcome, str) else str(outcome)
                self._event(events, "FINISH", attempt, "goal completed with verified outcome")
                return BrainResult(
                    answer=answer,
                    verified=True,
                    attempts=attempt,
                    events=tuple(events),
                )

            observation = observe(goal)
            self._event(
                events,
                "OBSERVE",
                attempt,
                "goal context refreshed after failed verification",
            )

        raise BrainError("autonomous run exhausted verification attempts")

    def run_answer(self, goal: str, action: Callable[[], str]) -> BrainResult:
        """Execute one answer action through the autonomous control loop."""
        return self.run(
            goal=goal,
            observe=lambda current_goal: {"goal": current_goal},
            plan=lambda current_goal, observation, attempt: {
                "action": "answer",
                "attempt": attempt,
            },
            act=lambda action_plan, attempt: action(),
            verify=lambda current_goal, outcome, observation: (
                isinstance(outcome, str) and bool(outcome.strip())
            ),
        )
