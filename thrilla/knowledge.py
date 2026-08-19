"""Direct owner-memory and self-knowledge providers."""

from typing import Callable

from .answers import AnswerContext, Evidence, KnowledgeGap
from .capabilities import self_description
from .memory import HybridMemory
from .providers import EvidenceProvider


class OwnerMemoryProvider(EvidenceProvider):
    """Answer durable owner-memory questions without model inference."""

    def __init__(
        self,
        memory: HybridMemory,
        owner_name_fn: Callable[[], str],
    ) -> None:
        self.memory = memory
        self.owner_name_fn = owner_name_fn

    def supports(self, prompt: str) -> bool:
        return self.memory.can_answer_owner_query(prompt)

    def collect(self, prompt: str) -> AnswerContext:
        answer = self.memory.answer_owner_query(
            prompt,
            configured_owner_name=self.owner_name_fn(),
        )

        if answer is None:
            return AnswerContext(
                gap=KnowledgeGap(
                    unknown="requested durable owner fact",
                    missing_evidence=(
                        "matching active durable owner memory",
                    ),
                    reason=(
                        "No matching active owner fact is stored."
                    ),
                    resolution=(
                        "tell Thrilla the fact",
                        "use /remember <fact>",
                    ),
                )
            )

        return AnswerContext(
            direct_answer=answer,
            evidence=(
                Evidence(
                    source="durable_owner_memory",
                    detail=(
                        "Read from Thrilla's local durable hybrid "
                        "memory store without model inference."
                    ),
                    content=answer,
                ),
            ),
        )


class SelfKnowledgeProvider(EvidenceProvider):
    """Answer identity/capability questions from code-owned facts."""

    _TERMS = (
        "who are you",
        "what are you",
        "what is your name",
        "what's your name",
        "who made you",
        "who created you",
        "who is your creator",
        "who owns you",
        "who is your owner",
        "what can you do",
        "what are your capabilities",
        "what do you know about yourself",
    )

    def __init__(
        self,
        owner_name_fn: Callable[[], str],
    ) -> None:
        self.owner_name_fn = owner_name_fn

    def supports(self, prompt: str) -> bool:
        lowered = " ".join(prompt.lower().split())
        return any(term in lowered for term in self._TERMS)

    def collect(self, prompt: str) -> AnswerContext:
        del prompt

        answer = self_description(
            owner_name=self.owner_name_fn(),
        )

        return AnswerContext(
            direct_answer=answer,
            evidence=(
                Evidence(
                    source="thrilla_identity_capabilities",
                    detail=(
                        "Generated from Thrilla's code-owned identity "
                        "and active-stage capability registry."
                    ),
                    content=answer,
                ),
            ),
        )
