"""Bounded autonomous task execution for Thrilla Stage 7C/7D."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from .tools import (
    ToolExecutor,
    ToolPermission,
)


class AutonomousError(RuntimeError):
    """Base Stage-7 autonomous execution error."""


class AutonomousProtocolError(
    AutonomousError
):
    """Planner or critic violated the autonomous protocol."""


class AutonomousBudgetError(
    AutonomousProtocolError
):
    """An explicit autonomy budget was exhausted."""


class AutonomousUnknownToolError(
    AutonomousProtocolError
):
    """Planner selected a tool outside Thrilla's registered surface."""


_ALLOWED_PERMISSIONS = {
    ToolPermission.READ,
    ToolPermission.EXECUTE,
    ToolPermission.DEVICE,
}


@dataclass(frozen=True)
class AutonomousBudget:
    max_steps: int = 8
    max_tool_calls: int = 8
    max_replans: int = 3
    max_tool_failures: int = 3
    max_protocol_errors: int = 2
    max_repeat_actions: int = 2


@dataclass(frozen=True)
class AutonomousAction:
    action: str
    tool: str = ""
    arguments: Mapping[str, Any] = None
    reason: str = ""
    answer: str = ""

    def __post_init__(self):
        if self.arguments is None:
            object.__setattr__(
                self,
                "arguments",
                {},
            )


@dataclass(frozen=True)
class CriticDecision:
    verdict: str
    reason: str = ""


@dataclass(frozen=True)
class AutonomousStep:
    number: int
    tool: str
    arguments: Mapping[str, Any]
    ok: bool
    permission: str
    output: Any
    error: str
    duration_ms: int
    evidence_count: int
    failure_kind: str = ""


@dataclass(frozen=True)
class AutonomousResult:
    goal: str
    completed: bool
    answer: str
    steps: Tuple[AutonomousStep, ...]
    tool_calls: int
    evidence_count: int
    replans: int = 0
    tool_failures: int = 0
    protocol_errors: int = 0
    critic_checks: int = 0
    loop_blocks: int = 0

    def __str__(self) -> str:
        return self.answer


class AutonomousTaskRunner:
    """Plan, execute, critique and recover within explicit budgets."""

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        planner: Callable,
        workspace: Path,
        critic: Optional[Callable] = None,
        max_steps: int = 8,
        max_tool_calls: Optional[int] = None,
        max_replans: int = 3,
        max_tool_failures: int = 3,
        max_protocol_errors: int = 2,
        max_repeat_actions: int = 2,
        observation_chars: int = 6000,
    ) -> None:
        if int(max_steps) < 1:
            raise ValueError(
                "max_steps must be at least 1"
            )

        self.tool_executor = tool_executor
        self.planner = planner
        self.critic = critic

        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        steps = min(
            int(max_steps),
            32,
        )

        calls = (
            steps
            if max_tool_calls is None
            else int(max_tool_calls)
        )

        if calls < 1:
            raise ValueError(
                "max_tool_calls must be at least 1"
            )

        self.budget = AutonomousBudget(
            max_steps=steps,
            max_tool_calls=min(
                calls,
                64,
            ),
            max_replans=max(
                0,
                min(
                    int(max_replans),
                    16,
                ),
            ),
            max_tool_failures=max(
                0,
                min(
                    int(max_tool_failures),
                    16,
                ),
            ),
            max_protocol_errors=max(
                0,
                min(
                    int(max_protocol_errors),
                    16,
                ),
            ),
            max_repeat_actions=max(
                1,
                min(
                    int(max_repeat_actions),
                    8,
                ),
            ),
        )

        # Preserve Stage-7C public attribute.
        self.max_steps = (
            self.budget.max_steps
        )

        self.observation_chars = max(
            1000,
            min(
                int(observation_chars),
                30000,
            ),
        )

    @property
    def tool_catalog(
        self,
    ) -> Tuple[Dict[str, str], ...]:
        allowed = []

        for item in (
            self.tool_executor
            .registry
            .catalog
        ):
            permission = ToolPermission(
                item["permission"]
            )

            if permission in _ALLOWED_PERMISSIONS:
                allowed.append(
                    dict(item)
                )

        return tuple(allowed)

    def _system_prompt(
        self,
    ) -> str:
        tools = json.dumps(
            self.tool_catalog,
            indent=2,
            sort_keys=True,
        )

        budget = json.dumps(
            {
                "max_steps":
                    self.budget.max_steps,
                "max_tool_calls":
                    self.budget.max_tool_calls,
                "max_replans":
                    self.budget.max_replans,
                "max_tool_failures":
                    self.budget.max_tool_failures,
                "max_protocol_errors":
                    self.budget.max_protocol_errors,
                "max_repeat_actions":
                    self.budget.max_repeat_actions,
            },
            indent=2,
            sort_keys=True,
        )

        return (
            "You are Thrilla's Stage 7 autonomous task planner.\n"
            "Break the owner's goal into the smallest useful tool steps.\n"
            "You may only select tools from TOOL CATALOG.\n"
            "Never invent tool names.\n"
            "Never claim a tool succeeded unless its observation says ok=true.\n"
            "Use evidence from prior observations before finishing.\n"
            "React to RECOVERY / CRITIC / OWNER notes before choosing again.\n"
            "Do not repeat an action that has been blocked as a loop.\n"
            "Paths may be relative to WORKSPACE.\n"
            "Return exactly one JSON object and no prose.\n\n"
            "For a tool step:\n"
            '{"action":"tool","tool":"<name>",'
            '"arguments":{},"reason":"<short reason>"}\n\n'
            "To finish:\n"
            '{"action":"finish","answer":"<final answer>"}\n\n'
            "WORKSPACE:\n"
            + str(self.workspace)
            + "\n\nAUTONOMY BUDGET:\n"
            + budget
            + "\n\nTOOL CATALOG:\n"
            + tools
        )

    @staticmethod
    def _json_object(
        value: str,
    ) -> Mapping[str, Any]:
        text = str(value).strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip()
                == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(
                lines
            ).strip()

        start = text.find("{")
        end = text.rfind("}")

        if (
            start < 0
            or end < start
        ):
            raise AutonomousProtocolError(
                "planner did not return a JSON object"
            )

        try:
            payload = json.loads(
                text[
                    start : end + 1
                ]
            )
        except json.JSONDecodeError as error:
            raise AutonomousProtocolError(
                "planner returned invalid JSON"
            ) from error

        if not isinstance(
            payload,
            dict,
        ):
            raise AutonomousProtocolError(
                "planner JSON must be an object"
            )

        return payload

    def _parse_action(
        self,
        raw: str,
    ) -> AutonomousAction:
        payload = self._json_object(
            raw
        )

        action = str(
            payload.get(
                "action",
                "",
            )
        ).strip().lower()

        if action == "finish":
            answer = str(
                payload.get(
                    "answer",
                    "",
                )
            ).strip()

            if not answer:
                raise AutonomousProtocolError(
                    "finish action requires a non-empty answer"
                )

            return AutonomousAction(
                action="finish",
                answer=answer,
            )

        if action != "tool":
            raise AutonomousProtocolError(
                "planner action must be tool or finish"
            )

        tool = str(
            payload.get(
                "tool",
                "",
            )
        ).strip()

        if (
            not tool
            or tool
            not in self.tool_executor.registry.names
        ):
            raise AutonomousUnknownToolError(
                "planner selected unknown tool: {0}".format(
                    tool or "<empty>"
                )
            )

        spec = (
            self.tool_executor
            .registry
            .get(tool)
        )

        if (
            spec.permission
            not in _ALLOWED_PERMISSIONS
        ):
            raise AutonomousProtocolError(
                "planner selected disallowed permission: {0}".format(
                    spec.permission.value
                )
            )

        arguments = payload.get(
            "arguments",
            {},
        )

        if not isinstance(
            arguments,
            dict,
        ):
            raise AutonomousProtocolError(
                "tool arguments must be a JSON object"
            )

        return AutonomousAction(
            action="tool",
            tool=tool,
            arguments=dict(arguments),
            reason=str(
                payload.get(
                    "reason",
                    "",
                )
            ).strip(),
        )

    def _parse_critic(
        self,
        raw: str,
    ) -> CriticDecision:
        payload = self._json_object(
            raw
        )

        verdict = str(
            payload.get(
                "verdict",
                "",
            )
        ).strip().lower()

        if verdict not in {
            "accept",
            "replan",
        }:
            raise AutonomousProtocolError(
                "critic verdict must be accept or replan"
            )

        return CriticDecision(
            verdict=verdict,
            reason=str(
                payload.get(
                    "reason",
                    "",
                )
            ).strip(),
        )

    def _arguments(
        self,
        arguments: Mapping[str, Any],
    ) -> Dict[str, Any]:
        resolved = dict(
            arguments
        )

        for name in (
            "path",
            "cwd",
        ):
            value = resolved.get(
                name
            )

            if (
                isinstance(value, str)
                and value
            ):
                candidate = Path(
                    value
                ).expanduser()

                if not candidate.is_absolute():
                    resolved[name] = str(
                        (
                            self.workspace
                            / candidate
                        ).resolve()
                    )

        return resolved

    @staticmethod
    def _failure_kind(
        error: str,
    ) -> str:
        lowered = str(
            error
        ).lower()

        if (
            "filenotfounderror"
            in lowered
            or "no such file"
            in lowered
        ):
            return "missing"

        if (
            "permissionerror"
            in lowered
            or "permission denied"
            in lowered
            or "not enabled"
            in lowered
        ):
            return "permission"

        if (
            "timeout"
            in lowered
            or "timed out"
            in lowered
        ):
            return "timeout"

        if (
            "notadirectoryerror"
            in lowered
        ):
            return "path"

        return "tool"

    def _observation(
        self,
        step: AutonomousStep,
    ) -> str:
        payload = {
            "step": step.number,
            "tool": step.tool,
            "ok": step.ok,
            "permission":
                step.permission,
            "failure_kind":
                step.failure_kind,
            "error": step.error,
            "duration_ms":
                step.duration_ms,
            "evidence_count":
                step.evidence_count,
            "output": step.output,
        }

        text = json.dumps(
            payload,
            default=str,
            sort_keys=True,
        )

        return text[
            : self.observation_chars
        ]

    def _messages(
        self,
        goal: str,
        steps: Sequence[
            AutonomousStep
        ],
        notes: Sequence[str] = (),
    ):
        if steps:
            observations = "\n".join(
                self._observation(
                    step
                )
                for step in steps
            )
        else:
            observations = (
                "No tools have been "
                "executed yet."
            )

        note_text = (
            "\n".join(
                "- " + str(note)
                for note in notes
            )
            if notes
            else "None."
        )

        return [
            {
                "role": "system",
                "content":
                    self._system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    "OWNER GOAL:\n"
                    + str(goal)
                    + "\n\nOBSERVATIONS:\n"
                    + observations
                    + "\n\nRECOVERY / CRITIC / OWNER NOTES:\n"
                    + note_text
                    + "\n\nChoose the next action."
                ),
            },
        ]

    def _critic_messages(
        self,
        goal: str,
        answer: str,
        steps: Sequence[
            AutonomousStep
        ],
    ):
        observations = (
            "\n".join(
                self._observation(
                    step
                )
                for step in steps
            )
            if steps
            else "No tool evidence."
        )

        return [
            {
                "role": "system",
                "content": (
                    "You are Thrilla's independent Critic gate.\n"
                    "Determine whether the proposed completion is actually "
                    "supported by the goal and observations.\n"
                    "Reject unsupported success claims.\n"
                    "Do not demand tools when the goal can be correctly "
                    "completed without tools.\n"
                    "Return exactly one JSON object:\n"
                    '{"verdict":"accept","reason":"..."}\n'
                    "or\n"
                    '{"verdict":"replan","reason":"..."}'
                ),
            },
            {
                "role": "user",
                "content": (
                    "OWNER GOAL:\n"
                    + goal
                    + "\n\nPROPOSED ANSWER:\n"
                    + answer
                    + "\n\nOBSERVATIONS:\n"
                    + observations
                ),
            },
        ]

    @staticmethod
    def _fingerprint(
        tool: str,
        arguments: Mapping[
            str,
            Any,
        ],
    ) -> str:
        return (
            tool
            + ":"
            + json.dumps(
                dict(arguments),
                sort_keys=True,
                default=str,
            )
        )

    def run(
        self,
        goal: str,
        *,
        job_context=None,
    ) -> AutonomousResult:
        goal = str(
            goal
        ).strip()

        if not goal:
            raise AutonomousProtocolError(
                "autonomous goal must not be empty"
            )

        steps = []
        notes = []

        evidence_count = 0
        replans = 0
        tool_failures = 0
        protocol_errors = 0
        critic_checks = 0
        loop_blocks = 0
        tool_calls = 0

        last_fingerprint = None
        repeat_count = 0

        def add_directives(
            directives,
        ):
            nonlocal replans

            for directive in (
                directives or ()
            ):
                value = str(
                    directive
                ).strip()

                if value:
                    notes.append(
                        "OWNER DIRECTIVE: "
                        + value
                    )

        for decision_number in range(
            1,
            self.budget.max_steps + 1,
        ):
            if job_context is not None:
                directives = (
                    job_context.checkpoint(
                        "autonomy.plan.{0}".format(
                            decision_number
                        ),
                        next_action=(
                            "autonomy.execute.{0}".format(
                                decision_number
                            )
                        ),
                        completed_steps=(
                            len(steps)
                        ),
                        total_steps=(
                            self.budget.max_steps
                        ),
                        evidence_count=(
                            evidence_count
                        ),
                    )
                )

                add_directives(
                    directives
                )

            raw = self.planner(
                self._messages(
                    goal,
                    steps,
                    notes,
                ),
                "system",
            )

            try:
                action = self._parse_action(
                    raw
                )
            except AutonomousUnknownToolError:
                raise
            except AutonomousProtocolError as error:
                protocol_errors += 1

                if (
                    protocol_errors
                    > self.budget.max_protocol_errors
                ):
                    raise AutonomousBudgetError(
                        "autonomous protocol-error budget exhausted"
                    ) from error

                notes.append(
                    "RECOVERY: Planner protocol error: "
                    + str(error)
                    + ". Return valid JSON next."
                )
                continue

            if (
                action.action
                == "finish"
            ):
                if self.critic is not None:
                    critic_checks += 1

                    try:
                        decision = (
                            self._parse_critic(
                                self.critic(
                                    self._critic_messages(
                                        goal,
                                        action.answer,
                                        steps,
                                    ),
                                    "system",
                                )
                            )
                        )
                    except AutonomousProtocolError as error:
                        protocol_errors += 1

                        if (
                            protocol_errors
                            > self.budget.max_protocol_errors
                        ):
                            raise AutonomousBudgetError(
                                "autonomous protocol-error budget exhausted"
                            ) from error

                        notes.append(
                            "RECOVERY: Critic protocol error: "
                            + str(error)
                        )
                        continue

                    if (
                        decision.verdict
                        == "replan"
                    ):
                        replans += 1

                        if (
                            replans
                            > self.budget.max_replans
                        ):
                            raise AutonomousBudgetError(
                                "autonomous replan budget exhausted"
                            )

                        notes.append(
                            "CRITIC REPLAN: "
                            + (
                                decision.reason
                                or "completion was not verified"
                            )
                        )
                        continue

                if job_context is not None:
                    job_context.checkpoint(
                        "autonomy.finish",
                        next_action="finish",
                        completed_steps=(
                            len(steps)
                        ),
                        total_steps=(
                            len(steps)
                        ),
                        progress=1.0,
                        evidence_count=(
                            evidence_count
                        ),
                    )

                return AutonomousResult(
                    goal=goal,
                    completed=True,
                    answer=action.answer,
                    steps=tuple(steps),
                    tool_calls=tool_calls,
                    evidence_count=(
                        evidence_count
                    ),
                    replans=replans,
                    tool_failures=(
                        tool_failures
                    ),
                    protocol_errors=(
                        protocol_errors
                    ),
                    critic_checks=(
                        critic_checks
                    ),
                    loop_blocks=(
                        loop_blocks
                    ),
                )

            arguments = self._arguments(
                action.arguments
            )

            fingerprint = (
                self._fingerprint(
                    action.tool,
                    arguments,
                )
            )

            if (
                fingerprint
                == last_fingerprint
            ):
                repeat_count += 1
            else:
                last_fingerprint = (
                    fingerprint
                )
                repeat_count = 1

            if (
                repeat_count
                > self.budget.max_repeat_actions
            ):
                loop_blocks += 1
                replans += 1

                if (
                    replans
                    > self.budget.max_replans
                ):
                    raise AutonomousBudgetError(
                        "autonomous replan budget exhausted after loop detection"
                    )

                notes.append(
                    "RECOVERY: Repeated action blocked as a loop. "
                    "Choose a different action or finish from existing evidence."
                )

                # Reset so the planner gets one clean chance to change course.
                last_fingerprint = None
                repeat_count = 0

                continue

            if (
                tool_calls
                >= self.budget.max_tool_calls
            ):
                raise AutonomousBudgetError(
                    "autonomous tool-call budget exhausted"
                )

            tool_calls += 1

            result = (
                self.tool_executor.execute(
                    action.tool,
                    arguments,
                )
            )

            failure_kind = ""

            if not result.ok:
                tool_failures += 1
                failure_kind = (
                    self._failure_kind(
                        result.error
                    )
                )

                if (
                    tool_failures
                    > self.budget.max_tool_failures
                ):
                    raise AutonomousBudgetError(
                        "autonomous tool-failure budget exhausted"
                    )

                notes.append(
                    "RECOVERY: Tool failure classified as "
                    + failure_kind
                    + ". Use the observation and choose another action."
                )

            step = AutonomousStep(
                number=len(steps) + 1,
                tool=action.tool,
                arguments=arguments,
                ok=result.ok,
                permission=(
                    result.permission.value
                ),
                output=result.output,
                error=result.error,
                duration_ms=(
                    result.duration_ms
                ),
                evidence_count=len(
                    result.evidence
                ),
                failure_kind=(
                    failure_kind
                ),
            )

            steps.append(
                step
            )

            evidence_count += len(
                result.evidence
            )

            if job_context is not None:
                directives = (
                    job_context.checkpoint(
                        "autonomy.execute.{0}".format(
                            len(steps)
                        ),
                        next_action=(
                            "autonomy.plan.{0}".format(
                                decision_number + 1
                            )
                        ),
                        completed_steps=(
                            len(steps)
                        ),
                        total_steps=(
                            self.budget.max_steps
                        ),
                        progress=min(
                            1.0,
                            decision_number
                            / float(
                                self.budget.max_steps
                            ),
                        ),
                        evidence_count=(
                            evidence_count
                        ),
                    )
                )

                add_directives(
                    directives
                )

        raise AutonomousBudgetError(
            "autonomous step limit exhausted "
            "before verified finish"
        )
