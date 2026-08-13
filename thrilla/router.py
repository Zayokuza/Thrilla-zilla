"""Transparent deterministic request routing for the first Thrilla core."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Tuple


class Route(str, Enum):
    GENERAL = "general-chat"
    CODING = "coding"
    DEEP_SEARCH = "deep-search"
    FILES = "files"
    DATA = "data"
    DEVICE = "device"
    SYSTEM = "system"


KEYWORDS: Dict[Route, Tuple[str, ...]] = {
    Route.CODING: (
        "code", "bug", "debug", "compile", "build", "repository", "repo",
        "python", "javascript", "typescript", "rust", "function", "test",
    ),
    Route.DEEP_SEARCH: (
        "search", "research", "source", "verify", "latest", "news", "osint",
        "archive", "website", "web",
    ),
    Route.FILES: (
        "file", "folder", "directory", "document", "pdf", "zip", "rename",
        "copy", "move",
    ),
    Route.DATA: (
        "data", "csv", "json", "database", "sql", "spreadsheet", "chart",
        "analyze", "statistics",
    ),
    Route.DEVICE: (
        "android", "phone", "termux", "battery", "camera", "storage", "wifi",
        "bluetooth", "device", "s24",
    ),
    Route.SYSTEM: (
        "system", "process", "service", "memory", "cpu", "ram", "disk", "shell",
        "command", "windows", "powershell", "install", "permission",
    ),
}

PRIORITY = (
    Route.CODING,
    Route.DEEP_SEARCH,
    Route.FILES,
    Route.DATA,
    Route.DEVICE,
    Route.SYSTEM,
)


@dataclass(frozen=True)
class RouteDecision:
    route: Route
    confidence: float
    matches: Tuple[str, ...]

    @property
    def explanation(self) -> str:
        if not self.matches:
            return "No specialist signal found; using general chat."
        return "Matched: " + ", ".join(self.matches)


def _tokens(text: str) -> Iterable[str]:
    return re.findall(r"[a-z0-9.+#-]+", text.lower())


def route_request(text: str) -> RouteDecision:
    tokens = set(_tokens(text))
    scores: List[Tuple[int, int, Route, Tuple[str, ...]]] = []
    for priority, route in enumerate(PRIORITY):
        matches = tuple(keyword for keyword in KEYWORDS[route] if keyword in tokens)
        if matches:
            scores.append((len(matches), -priority, route, matches))
    if not scores:
        return RouteDecision(Route.GENERAL, 0.55, ())
    count, _, route, matches = max(scores)
    confidence = min(0.98, 0.62 + (count - 1) * 0.09)
    return RouteDecision(route, confidence, matches)

