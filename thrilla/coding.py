"""Checkpointed autonomous coding workflow for Thrilla."""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence, Tuple

from .checkpoints import CheckpointManager
from .performance import RepositoryIndex


class CodingPlanError(RuntimeError):
    """A repair plan was invalid or could not be safely applied."""


@dataclass(frozen=True)
class FileEdit:
    path: str
    content: str


@dataclass(frozen=True)
class VerificationRecord:
    argv: Tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class CriticReport:
    passed: bool
    detail: str


@dataclass(frozen=True)
class CodingOutcome:
    ok: bool
    rolled_back: bool
    checkpoint_id: str
    edited_paths: Tuple[str, ...]
    verification: Tuple[VerificationRecord, ...]
    critic: CriticReport
    summary: str


class RepositoryInspector:
    SUPPORTED_SUFFIXES = {
        ".py", ".md", ".txt", ".json", ".toml",
        ".yaml", ".yml", ".sh", ".cmd", ".ps1",
    }
    SEARCH_ROOTS = ("thrilla", "tests", "docs", "bin")
    STOP_WORDS = {
        "the", "and", "for", "with", "that", "this", "from",
        "your", "itself", "please", "make", "fix", "repair",
    }

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.index = RepositoryIndex(
            self.repo_root,
            search_roots=self.SEARCH_ROOTS,
            supported_suffixes=self.SUPPORTED_SUFFIXES,
        )

    @staticmethod
    def _tokens(goal: str) -> Tuple[str, ...]:
        result = []
        seen = set()
        for token in re.findall(r"[a-zA-Z0-9_]+", goal.lower()):
            if len(token) < 3 or token in RepositoryInspector.STOP_WORDS:
                continue
            if token not in seen:
                seen.add(token)
                result.append(token)
        return tuple(result)

    def find_candidates(self, goal: str, max_files: int = 3) -> Tuple[str, ...]:
        limit = max(1, min(int(max_files), 10))
        tokens = self._tokens(goal)

        candidates = self.index.rank(
            tokens,
            max_files=limit,
        )

        if candidates:
            return candidates

        defaults = (
            "thrilla/app.py",
            "thrilla/brain.py",
            "thrilla/tools.py",
            "thrilla/experts.py",
            "tests/test_universal_ask.py",
        )

        return tuple(
            value
            for value in defaults
            if (self.repo_root / value).is_file()
        )[:limit]



class RepositoryCodingWorkflow:
    """Apply bounded text edits, verify them, and rollback on failure."""

    SUPPORTED_SUFFIXES = RepositoryInspector.SUPPORTED_SUFFIXES

    def __init__(
        self,
        repo_root: Path,
        state_root: Path,
        verification_timeout: float = 180.0,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.state_root = Path(state_root).expanduser().resolve()
        self.verification_timeout = max(1.0, min(float(verification_timeout), 1800.0))
        self.checkpoints = CheckpointManager(self.repo_root, self.state_root)

    def _resolve_edit_path(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise CodingPlanError("edit path must be a non-empty string")
        relative = Path(value)
        if relative.is_absolute():
            raise CodingPlanError("edit path must be repository-relative")
        candidate = (self.repo_root / relative).resolve()
        if candidate == self.repo_root or self.repo_root not in candidate.parents:
            raise CodingPlanError("edit path escapes repository root")
        if ".git" in candidate.relative_to(self.repo_root).parts:
            raise CodingPlanError("editing .git is forbidden")
        if candidate.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise CodingPlanError(
                "unsupported editable file type: {}".format(candidate.suffix)
            )
        return candidate

    def _normalize_edits(self, edits: Iterable[FileEdit]) -> Tuple[FileEdit, ...]:
        normalized = []
        seen = set()
        total_chars = 0
        for edit in edits:
            if not isinstance(edit, FileEdit):
                raise CodingPlanError("edits must be FileEdit values")
            path = self._resolve_edit_path(edit.path)
            relative = str(path.relative_to(self.repo_root))
            if relative in seen:
                raise CodingPlanError("repair plan edits one path twice")
            if not isinstance(edit.content, str):
                raise CodingPlanError("edit content must be text")
            total_chars += len(edit.content)
            normalized.append(FileEdit(relative, edit.content))
            seen.add(relative)
        if not normalized:
            raise CodingPlanError("repair plan proposed no file edits")
        if len(normalized) > 8:
            raise CodingPlanError("repair plan may edit at most 8 files")
        if total_chars > 300_000:
            raise CodingPlanError("repair plan exceeds 300000-character edit budget")
        return tuple(normalized)

    @staticmethod
    def _default_verification_commands() -> Tuple[Tuple[str, ...], ...]:
        return (
            (sys.executable, "-m", "compileall", "-q", "thrilla", "tests"),
            (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"),
        )

    def _write_edits(self, edits: Sequence[FileEdit]) -> None:
        for edit in edits:
            target = self._resolve_edit_path(edit.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".thrilla-write-tmp")
            temporary.write_text(edit.content, encoding="utf-8")
            os.replace(temporary, target)

    def _run_verification(
        self,
        commands: Sequence[Sequence[str]],
    ) -> Tuple[VerificationRecord, ...]:
        records = []
        for command in commands:
            argv = tuple(str(part) for part in command)
            if not argv:
                raise CodingPlanError("verification command may not be empty")
            try:
                completed = subprocess.run(
                    list(argv),
                    cwd=str(self.repo_root),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,
                    timeout=self.verification_timeout,
                    check=False,
                )
                record = VerificationRecord(
                    argv,
                    completed.returncode,
                    completed.stdout[-30000:],
                    completed.stderr[-30000:],
                    False,
                )
            except subprocess.TimeoutExpired as error:
                stdout = error.stdout.decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
                stderr = error.stderr.decode("utf-8", errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
                record = VerificationRecord(
                    argv, 124, stdout[-30000:], stderr[-30000:], True
                )
            records.append(record)
            if record.returncode != 0:
                break
        return tuple(records)

    def _critic_review(
        self,
        edits: Sequence[FileEdit],
        verification: Sequence[VerificationRecord],
    ) -> CriticReport:
        if not verification:
            return CriticReport(False, "no verification records were produced")
        for record in verification:
            if record.returncode != 0:
                return CriticReport(
                    False,
                    "verification failed: {} exited {}".format(
                        " ".join(record.argv), record.returncode
                    ),
                )
        for edit in edits:
            if not self._resolve_edit_path(edit.path).is_file():
                return CriticReport(False, "edited file is missing: {}".format(edit.path))
        try:
            diff_check = subprocess.run(
                ["git", "diff", "--check"],
                cwd=str(self.repo_root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                timeout=30.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return CriticReport(False, "git diff --check could not run: {}".format(error))
        if diff_check.returncode != 0:
            return CriticReport(
                False,
                "git diff --check failed: " + (diff_check.stdout + diff_check.stderr)[-2000:],
            )
        return CriticReport(True, "verification passed and git diff --check is clean")

    def apply_edits(
        self,
        goal: str,
        edits: Iterable[FileEdit],
        verification_commands: Optional[Sequence[Sequence[str]]] = None,
    ) -> CodingOutcome:
        normalized = self._normalize_edits(edits)
        checkpoint = self.checkpoints.create(edit.path for edit in normalized)
        try:
            self._write_edits(normalized)
            commands = (
                tuple(tuple(str(part) for part in command) for command in verification_commands)
                if verification_commands is not None
                else self._default_verification_commands()
            )
            verification = self._run_verification(commands)
            critic = self._critic_review(normalized, verification)
            if not critic.passed:
                self.checkpoints.rollback(checkpoint)
                return CodingOutcome(
                    False,
                    True,
                    checkpoint.checkpoint_id,
                    tuple(edit.path for edit in normalized),
                    verification,
                    critic,
                    "Repair verification failed; checkpoint restored. " + critic.detail,
                )
            return CodingOutcome(
                True,
                False,
                checkpoint.checkpoint_id,
                tuple(edit.path for edit in normalized),
                verification,
                critic,
                "Repair verified successfully for goal: {}".format(goal),
            )
        except Exception:
            self.checkpoints.rollback(checkpoint)
            raise


class AutonomousCodingAgent:
    """Ask the local model for candidate-file edits, then verify locally."""

    def __init__(
        self,
        repo_root: Path,
        state_root: Path,
        model_chat: Callable[[Sequence[Mapping[str, str]], str], str],
        verification_timeout: float = 180.0,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.inspector = RepositoryInspector(self.repo_root)
        self.workflow = RepositoryCodingWorkflow(
            self.repo_root, state_root, verification_timeout
        )
        self.model_chat = model_chat

    @staticmethod
    def _extract_json(text: str) -> Mapping[str, object]:
        if not isinstance(text, str):
            raise CodingPlanError("model repair plan was not text")
        stripped = text.strip()
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, count=1, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped, count=1)
        first = stripped.find("{")
        last = stripped.rfind("}")
        if first < 0 or last < first:
            raise CodingPlanError("model did not return a JSON repair plan")
        try:
            payload = json.loads(stripped[first:last + 1])
        except json.JSONDecodeError as error:
            raise CodingPlanError("model repair plan JSON is invalid: {}".format(error)) from error
        if not isinstance(payload, dict):
            raise CodingPlanError("model repair plan must be one JSON object")
        return payload

    def _candidate_context(self, goal: str, paths: Sequence[str]) -> str:
        blocks = []
        tokens = self.inspector._tokens(goal)

        for relative in paths:
            path = (self.repo_root / relative).resolve()
            if self.repo_root not in path.parents or not path.is_file():
                continue

            content = path.read_text(encoding="utf-8", errors="replace")
            lowered = content.lower()
            positions = [
                lowered.find(token)
                for token in tokens
                if lowered.find(token) >= 0
            ]
            position = min(positions) if positions else 0
            start = max(0, position - 700)
            excerpt = content[start:start + 2200]

            blocks.append(
                "===== FILE EXCERPT: {} @ {} =====\n{}".format(
                    relative, start, excerpt
                )
            )

        return "\n\n".join(blocks)

    def plan(
        self,
        goal: str,
        candidate_paths: Optional[Sequence[str]] = None,
    ) -> Tuple[str, Tuple[FileEdit, ...], Tuple[str, ...]]:
        candidates = tuple(
            candidate_paths if candidate_paths is not None
            else self.inspector.find_candidates(goal)
        )
        if not candidates:
            raise CodingPlanError("repository inspection found no candidate files")
        candidate_set = set(candidates)
        system = (
            "You are Thrilla-zilla's repository repair planner. Return JSON only. "
            "You may edit only the candidate paths supplied. Do not propose shell commands, "
            "git commands, deletions, renames, network actions, or paths outside the repository. "
            "Use exact text replacement patches. The 'old' text must be copied exactly from a supplied excerpt "
            "and must identify one unique occurrence; 'new' is the replacement text. Schema: "
            "{\"summary\":\"short explanation\",\"edits\":[{\"path\":\"relative/path\",\"old\":\"exact old text\",\"new\":\"replacement text\"}]}. "
            "If no safe repair can be determined, return {\"summary\":\"insufficient evidence\",\"edits\":[]}."
        )
        user = "OWNER GOAL:\n{}\n\nCANDIDATE FILES:\n{}\n\n{}".format(
            goal,
            "\n".join(candidates),
            self._candidate_context(goal, candidates),
        )
        response = self.model_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "coding",
        )
        payload = self._extract_json(response)
        summary = str(payload.get("summary", "")).strip()
        raw_edits = payload.get("edits")
        if not isinstance(raw_edits, list):
            raise CodingPlanError("model repair plan edits must be a JSON list")
        edits = []
        for item in raw_edits:
            if not isinstance(item, dict):
                raise CodingPlanError("each repair edit must be a JSON object")
            path = item.get("path")
            old = item.get("old")
            new = item.get("new")
            if (
                not isinstance(path, str)
                or not isinstance(old, str)
                or not isinstance(new, str)
                or not old
            ):
                raise CodingPlanError(
                    "each repair edit requires string path, non-empty old, and string new"
                )
            if path not in candidate_set:
                raise CodingPlanError(
                    "model proposed an edit outside inspected candidates: {}".format(path)
                )

            target = (self.repo_root / path).resolve()
            current = target.read_text(encoding="utf-8", errors="replace")
            occurrences = current.count(old)
            if occurrences != 1:
                raise CodingPlanError(
                    "model patch old text must match exactly once in {} (matched {})".format(
                        path, occurrences
                    )
                )

            edits.append(FileEdit(path, current.replace(old, new, 1)))
        if not edits:
            raise CodingPlanError(summary or "model proposed no safe file edits")
        return summary, tuple(edits), candidates

    def run(
        self,
        goal: str,
        verification_commands: Optional[Sequence[Sequence[str]]] = None,
        candidate_paths: Optional[Sequence[str]] = None,
    ) -> CodingOutcome:
        summary, edits, _ = self.plan(goal, candidate_paths)
        outcome = self.workflow.apply_edits(goal, edits, verification_commands)
        return CodingOutcome(
            outcome.ok,
            outcome.rolled_back,
            outcome.checkpoint_id,
            outcome.edited_paths,
            outcome.verification,
            outcome.critic,
            (summary + " — " + outcome.summary) if summary else outcome.summary,
        )
