"""Read-only discovery and verification of the external donor library."""

import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from .catalog import ALL_DONORS, CORE_DONORS, DonorSpec


@dataclass(frozen=True)
class DonorState:
    spec: DonorSpec
    path: Path
    state: str

    @property
    def present(self) -> bool:
        return self.state == "ready"


@dataclass(frozen=True)
class GitDetails:
    branch: str
    commit: str
    clean: Optional[bool]
    remote: str
    error: str = ""


class DonorRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser()

    def inspect(self, spec: DonorSpec) -> DonorState:
        path = self.root / spec.relative_path
        marker = path / ".git"
        if marker.is_dir() or marker.is_file():
            state = "ready"
        elif path.exists():
            state = "incomplete"
        else:
            state = "missing"
        return DonorState(spec, path, state)

    def scan(self, phase: Optional[int] = None) -> Tuple[DonorState, ...]:
        specs: Iterable[DonorSpec] = ALL_DONORS
        if phase is not None:
            specs = (spec for spec in specs if spec.phase == phase)
        return tuple(self.inspect(spec) for spec in specs)

    def progress(self, phase: int = 1) -> Tuple[int, int]:
        states = self.scan(phase)
        return sum(state.present for state in states), len(states)

    def priority_progress(self) -> Tuple[int, int]:
        states = tuple(self.inspect(spec) for spec in CORE_DONORS if spec.priority)
        return sum(state.present for state in states), len(states)

    def category_counts(self) -> Dict[int, Counter]:
        counts: Dict[int, Counter] = {}
        for state in self.scan(1):
            counts.setdefault(state.spec.category, Counter())[state.state] += 1
        return counts

    def verify_git(self, spec: DonorSpec, timeout: float = 4.0) -> GitDetails:
        state = self.inspect(spec)
        if not state.present:
            return GitDetails("", "", None, "", f"Repository is {state.state}.")

        def git(*arguments: str) -> str:
            result = subprocess.run(
                ["git", "-C", str(state.path), *arguments],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()

        try:
            branch = git("branch", "--show-current") or "detached"
            commit = git("rev-parse", "--short=12", "HEAD")
            remote = git("remote", "get-url", "origin")
            clean = not bool(git("status", "--porcelain"))
            return GitDetails(branch, commit, clean, remote)
        except (OSError, subprocess.SubprocessError) as error:
            return GitDetails("", "", None, "", str(error))

