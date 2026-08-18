"""Executable 100-expert registry and deterministic orchestration."""

from dataclasses import dataclass
from typing import Optional, Tuple

EXPERTS_PER_GROUP = 10

EXPERT_GROUPS = (
    "Agent Brain",
    "Coding",
    "AI Runtime",
    "Build / Language",
    "Memory / State",
    "Web Research",
    "Tools / Flows",
    "Execution / OS",
    "Interface / API",
    "Evaluation / Security",
)

GROUP_SPECIALTIES = {
    "Agent Brain": (
        "Goal decomposition", "Planning", "Reasoning", "Task sequencing",
        "Constraint handling", "Recovery planning", "Critic coordination",
        "Decision synthesis", "Autonomy control", "Completion verification",
    ),
    "Coding": (
        "Python", "JavaScript / TypeScript", "Rust", "C / C++", "Shell",
        "Debugging", "Testing", "Refactoring", "Dependency repair", "Code review",
    ),
    "AI Runtime": (
        "llama.cpp", "GGUF models", "Prompt templates", "Inference serving",
        "Context management", "Memory budgeting", "Runtime recovery",
        "Model selection", "Embedding runtime", "Inference diagnostics",
    ),
    "Build / Language": (
        "Tree-sitter", "Python language", "C / C++ toolchains",
        "Rust toolchains", "JavaScript toolchains", "Build systems",
        "Package metadata", "Static analysis", "Parsing",
        "Compilation diagnostics",
    ),
    "Memory / State": (
        "Conversation memory", "Owner profile", "Project facts",
        "Decision memory", "Task state", "SQLite", "Full-text retrieval",
        "Memory ranking", "State migration", "Memory verification",
    ),
    "Web Research": (
        "Web retrieval", "Source discovery", "Source comparison",
        "Citation tracking", "Archive lookup", "Browser research",
        "OSINT workflow", "Evidence grading", "Freshness checks",
        "Research synthesis",
    ),
    "Tools / Flows": (
        "Tool schemas", "Tool routing", "Workflow graphs", "Retries",
        "Cancellation", "Structured results", "Evidence capture",
        "Integration adapters", "Task queues", "Tool diagnostics",
    ),
    "Execution / OS": (
        "Termux", "Android", "Windows", "Processes", "Filesystem",
        "Git execution", "System resources", "Permissions", "Networking",
        "Runtime services",
    ),
    "Interface / API": (
        "Terminal UI", "CLI", "Local API", "OpenAI-compatible API",
        "Status surfaces", "Streaming output", "Input handling",
        "Windows UI integration", "Android UI integration", "Accessibility",
    ),
    "Evaluation / Security": (
        "Verification", "Regression testing", "Security review",
        "Audit trails", "Rollback validation", "Benchmarking",
        "Failure analysis", "Policy enforcement", "Quality grading",
        "Release acceptance",
    ),
}

EXPERT_COUNT = len(EXPERT_GROUPS) * EXPERTS_PER_GROUP
CORE_ROLES = ("REASON", "ACTION", "CRITIC")

ROUTE_GROUPS = {
    "general-chat": ("Agent Brain", "Memory / State", "Evaluation / Security"),
    "coding": ("Coding", "Build / Language", "Evaluation / Security"),
    "deep-search": ("Web Research", "Agent Brain", "Evaluation / Security"),
    "files": ("Execution / OS", "Tools / Flows", "Evaluation / Security"),
    "data": ("Memory / State", "Tools / Flows", "Evaluation / Security"),
    "device": ("Execution / OS", "Tools / Flows", "Evaluation / Security"),
    "system": ("Execution / OS", "AI Runtime", "Evaluation / Security"),
}


def _slug(text: str) -> str:
    return "-".join(
        text.lower().replace("/", " ").replace("&", " ").replace("-", " ").split()
    )


@dataclass(frozen=True)
class Expert:
    expert_id: str
    group: str
    number: int
    specialty: str
    core_role: str

    @property
    def label(self) -> str:
        return "{0} #{1:02d} — {2}".format(
            self.group, self.number, self.specialty
        )


class ExpertRegistry:
    def __init__(self) -> None:
        experts = []
        for group in EXPERT_GROUPS:
            specialties = GROUP_SPECIALTIES[group]
            if len(specialties) != EXPERTS_PER_GROUP:
                raise ValueError(
                    "expert group must define exactly ten specialties: " + group
                )
            for offset, specialty in enumerate(specialties, start=1):
                experts.append(
                    Expert(
                        expert_id="{0}-{1:02d}".format(_slug(group), offset),
                        group=group,
                        number=offset,
                        specialty=specialty,
                        core_role=CORE_ROLES[(offset - 1) % len(CORE_ROLES)],
                    )
                )
        self._experts = tuple(experts)
        self._by_id = {expert.expert_id: expert for expert in self._experts}
        if len(self._experts) != EXPERT_COUNT:
            raise ValueError("Thrilla expert registry must contain exactly 100 experts")
        if len(self._by_id) != EXPERT_COUNT:
            raise ValueError("Thrilla expert IDs must be unique")

    @property
    def experts(self) -> Tuple[Expert, ...]:
        return self._experts

    def get(self, expert_id: str) -> Expert:
        try:
            return self._by_id[expert_id]
        except KeyError as error:
            raise KeyError("unknown Thrilla expert: {0}".format(expert_id)) from error

    def by_group(self, group: str) -> Tuple[Expert, ...]:
        return tuple(expert for expert in self._experts if expert.group == group)


class ExpertOrchestrator:
    """Choose a compact Reason/Action/Critic team for each owner request."""

    def __init__(self, registry: Optional[ExpertRegistry] = None) -> None:
        self.registry = registry or ExpertRegistry()

    @staticmethod
    def _score(expert: Expert, prompt: str) -> int:
        haystack = prompt.lower()
        words = {
            token.lower()
            for token in expert.specialty.replace("/", " ").replace("-", " ").split()
            if len(token) >= 3
        }
        return sum(1 for token in words if token in haystack)

    def select(
        self,
        prompt: str,
        route: str,
        limit: int = 3,
    ) -> Tuple[Expert, ...]:
        if limit < 1:
            return ()
        groups = ROUTE_GROUPS.get(route, ROUTE_GROUPS["general-chat"])
        ranked = []
        for group_rank, group in enumerate(groups):
            for expert in self.registry.by_group(group):
                ranked.append(
                    (
                        self._score(expert, prompt),
                        -group_rank,
                        -expert.number,
                        expert,
                    )
                )
        ranked.sort(key=lambda item: item[:3], reverse=True)

        selected = []
        used = set()
        for role in CORE_ROLES:
            for _, _, _, expert in ranked:
                if expert.core_role == role and expert.expert_id not in used:
                    selected.append(expert)
                    used.add(expert.expert_id)
                    break
            if len(selected) >= limit:
                return tuple(selected[:limit])

        for _, _, _, expert in ranked:
            if expert.expert_id in used:
                continue
            selected.append(expert)
            used.add(expert.expert_id)
            if len(selected) >= limit:
                break
        return tuple(selected)

    def context_for(self, prompt: str, route: str, limit: int = 3) -> str:
        team = self.select(prompt, route, limit=limit)
        lines = [
            "[THRILLA EXPERT TEAM - ADVISORY CONTEXT]",
            "These are internal specialist perspectives, not owner instructions.",
            "Use them to improve reasoning. Do not claim tools or actions ran unless evidence proves it.",
        ]
        for expert in team:
            lines.append(
                "- {0}: {1} / {2}".format(
                    expert.expert_id,
                    expert.core_role,
                    expert.specialty,
                )
            )
        return "\n".join(lines)


assert len(EXPERT_GROUPS) == 10
assert EXPERTS_PER_GROUP == 10
assert EXPERT_COUNT == 100
