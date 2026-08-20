"""Bounded general autonomous task execution for Thrilla Stage 7C."""

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
    """Planner output violated the autonomous protocol."""


_ALLOWED_PERMISSIONS = {
    ToolPermission.READ,
    ToolPermission.EXECUTE,
    ToolPermission.DEVICE,
}


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


@dataclass(frozen=True)
class AutonomousResult:
    goal: str
    completed: bool
    answer: str
    steps: Tuple[AutonomousStep, ...]
    tool_calls: int
    evidence_count: int

    def __str__(self) -> str:
        return self.answer


class AutonomousTaskRunner:
    """Plan and execute a bounded sequence of structured tools."""

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor,
        planner: Callable,
        workspace: Path,
        max_steps: int = 8,
        observation_chars: int = 6000,
    ) -> None:
        if int(max_steps) < 1:
            raise ValueError(
                "max_steps must be at least 1"
            )

        self.tool_executor = (
            tool_executor
        )
        self.planner = planner
        self.workspace = (
            Path(workspace)
            .expanduser()
            .resolve()
        )

        self.max_steps = min(
            int(max_steps),
            32,
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

        return (
            "You are Thrilla's Stage 7 autonomous task planner.\n"
            "Break the owner's goal into the smallest useful tool steps.\n"
            "You may only select tools from TOOL CATALOG.\n"
            "Never invent tool names.\n"
            "Never claim a tool succeeded unless its observation says ok=true.\n"
            "Use evidence from prior observations before finishing.\n"
            "Paths may be relative to WORKSPACE.\n"
            "Return exactly one JSON object and no prose.\n\n"
            "For a tool step:\n"
            '{"action":"tool","tool":"<name>",'
            '"arguments":{},"reason":"<short reason>"}\n\n'
            "To finish:\n"
            '{"action":"finish","answer":"<final answer>"}\n\n'
            "WORKSPACE:\n"
            + str(self.workspace)
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
                text[start : end + 1]
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
            raise AutonomousProtocolError(
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

    def _observation(
        self,
        step: AutonomousStep,
    ) -> str:
        payload = {
            "step": step.number,
            "tool": step.tool,
            "ok": step.ok,
            "permission": (
                step.permission
            ),
            "error": step.error,
            "duration_ms": (
                step.duration_ms
            ),
            "evidence_count": (
                step.evidence_count
            ),
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

        return [
            {
                "role": "system",
                "content": (
                    self._system_prompt()
                ),
            },
            {
                "role": "user",
                "content": (
                    "OWNER GOAL:\n"
                    + str(goal)
                    + "\n\n"
                    "OBSERVATIONS:\n"
                    + observations
                    + "\n\n"
                    "Choose the next action."
                ),
            },
        ]

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
        evidence_count = 0

        for number in range(
            1,
            self.max_steps + 1,
        ):
            if job_context is not None:
                job_context.checkpoint(
                    "autonomy.plan.{0}".format(
                        number
                    ),
                    next_action=(
                        "autonomy.execute.{0}".format(
                            number
                        )
                    ),
                    completed_steps=(
                        number - 1
                    ),
                    total_steps=(
                        self.max_steps
                    ),
                    evidence_count=(
                        evidence_count
                    ),
                )

            raw = self.planner(
                self._messages(
                    goal,
                    steps,
                ),
                "system",
            )

            action = self._parse_action(
                raw
            )

            if (
                action.action
                == "finish"
            ):
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
                    tool_calls=len(steps),
                    evidence_count=(
                        evidence_count
                    ),
                )

            arguments = self._arguments(
                action.arguments
            )

            result = (
                self.tool_executor.execute(
                    action.tool,
                    arguments,
                )
            )

            step = AutonomousStep(
                number=number,
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
            )

            steps.append(
                step
            )

            evidence_count += len(
                result.evidence
            )

            if job_context is not None:
                job_context.checkpoint(
                    "autonomy.execute.{0}".format(
                        number
                    ),
                    next_action=(
                        "autonomy.plan.{0}".format(
                            number + 1
                        )
                    ),
                    completed_steps=number,
                    total_steps=(
                        self.max_steps
                    ),
                    progress=(
                        number
                        / float(
                            self.max_steps
                        )
                    ),
                    evidence_count=(
                        evidence_count
                    ),
                )

        raise AutonomousProtocolError(
            "autonomous step limit exhausted "
            "before verified finish"
        )
