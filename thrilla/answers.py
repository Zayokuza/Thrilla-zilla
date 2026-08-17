"""Answer evidence and knowledge-gap domain."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Evidence:
    """One observed or retrieved reference fact."""

    source: str
    detail: str
    content: str


@dataclass(frozen=True)
class KnowledgeGap:
    """Structured explanation of unavailable evidence."""

    unknown: str
    missing_evidence: Tuple[str, ...]
    reason: str
    resolution: Tuple[str, ...]


@dataclass(frozen=True)
class AnswerContext:
    """Evidence collected before final reasoning."""

    direct_answer: Optional[str] = None
    evidence: Tuple[Evidence, ...] = ()
    gap: Optional[KnowledgeGap] = None
