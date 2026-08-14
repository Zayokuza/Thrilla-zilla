"""Local model candidate metadata."""

from dataclasses import dataclass
from enum import Enum


class ModelRole(str, Enum):
    """Known purposes for discovered local models."""

    PRIMARY = "primary"
    CODING = "coding"
    PLANNER = "planner"
    EMBEDDING = "embedding"
    ALTERNATE = "alternate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ModelCandidate:
    """A discovered model and the metadata used to evaluate it."""

    path: str
    filename: str
    size_bytes: int
    architecture: str
    quantization: str
    role: ModelRole
    context_capability: int
    readable: bool
    compatibility: str
    source: str
    last_verified: str
    score: float
