"""Read-only observation providers for Universal Ask."""

from datetime import datetime
from typing import Callable, Optional

from .answers import (
    AnswerContext,
    Evidence,
    KnowledgeGap,
)
from .providers import EvidenceProvider


class ClockProvider(EvidenceProvider):
    """Observe the real local system clock."""

    _TERMS = (
        "what time",
        "current time",
        "time is it",
        "what date",
        "current date",
        "today's date",
        "todays date",
        "what day",
        "current day",
        "day is it",
    )

    def __init__(
        self,
        now_fn: Optional[
            Callable[[], datetime]
        ] = None,
    ) -> None:
        self._now_fn = (
            now_fn
            if now_fn is not None
            else datetime.now().astimezone
        )

    def supports(
        self,
        prompt: str,
    ) -> bool:
        lowered = prompt.lower()

        return any(
            term in lowered
            for term in self._TERMS
        )

    @staticmethod
    def _format_offset(
        value: datetime,
    ) -> str:
        offset = value.strftime("%z")

        if not offset:
            return "unknown"

        return (
            offset[:3]
            + ":"
            + offset[3:]
        )

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        del prompt

        now = self._now_fn()

        if now.tzinfo is None:
            now = now.astimezone()

        offset = self._format_offset(now)

        answer = (
            "Local date: {date}\n"
            "Local time: {time}\n"
            "Day: {day}\n"
            "UTC offset: {offset}"
        ).format(
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            day=now.strftime("%A"),
            offset=offset,
        )

        evidence = Evidence(
            source="system_clock",
            detail=(
                "Observed from the local system clock "
                "at collection time."
            ),
            content=answer,
        )

        return AnswerContext(
            direct_answer=answer,
            evidence=(evidence,),
        )


class RuntimeProvider(EvidenceProvider):
    """Observe the configured local model runtime."""

    _TERMS = (
        "is my model running",
        "is the model running",
        "model running",
        "local ai ready",
        "runtime ready",
        "runtime status",
        "what runtime",
        "what model is loaded",
        "which model is loaded",
        "model is loaded",
        "llama-server",
        "llama server",
        "why can't you answer with the model",
        "why cant you answer with the model",
    )

    def __init__(
        self,
        inspect_fn: Callable[
            [str, str],
            object,
        ],
        model_url: str,
        expected_model: str,
    ) -> None:
        self._inspect_fn = inspect_fn
        self.model_url = model_url
        self.expected_model = expected_model

    def supports(
        self,
        prompt: str,
    ) -> bool:
        lowered = prompt.lower()

        return any(
            term in lowered
            for term in self._TERMS
        )

    @staticmethod
    def _value(
        value: object,
        fallback: str = "unknown",
    ) -> str:
        if value is None:
            return fallback

        text = str(value).strip()

        return (
            text
            if text
            else fallback
        )

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        del prompt

        snapshot = self._inspect_fn(
            self.model_url,
            self.expected_model,
        )

        ready = bool(
            getattr(
                snapshot,
                "ready",
                False,
            )
        )

        endpoint = self._value(
            getattr(
                snapshot,
                "configured_endpoint",
                self.model_url,
            )
        )

        expected_model = self._value(
            getattr(
                snapshot,
                "expected_model",
                self.expected_model,
            ),
            "unspecified",
        )

        host = self._value(
            getattr(
                snapshot,
                "host",
                None,
            )
        )

        port_value = getattr(
            snapshot,
            "port",
            None,
        )

        port = self._value(
            port_value
        )

        reported_models = tuple(
            getattr(
                snapshot,
                "reported_models",
                (),
            )
            or ()
        )

        if reported_models:
            models = ", ".join(
                str(model)
                for model in reported_models
            )
        else:
            models = "none reported"

        detail = self._value(
            getattr(
                snapshot,
                "detail",
                None,
            )
        )

        error_value = getattr(
            snapshot,
            "error",
            "",
        )

        error = (
            self._value(error_value)
            if error_value
            else "none"
        )

        answer = (
            "Runtime ready: {ready}\n"
            "Configured endpoint: {endpoint}\n"
            "Expected model: {expected_model}\n"
            "Reported models: {models}\n"
            "Host: {host}:{port}\n"
            "Detail: {detail}\n"
            "Error: {error}"
        ).format(
            ready=(
                "yes"
                if ready
                else "no"
            ),
            endpoint=endpoint,
            expected_model=expected_model,
            models=models,
            host=host,
            port=port,
            detail=detail,
            error=error,
        )

        evidence = Evidence(
            source="runtime_status",
            detail=(
                "Observed from the configured local "
                "runtime through RuntimeManager "
                "inspection without creating a "
                "model client."
            ),
            content=answer,
        )

        return AnswerContext(
            direct_answer=answer,
            evidence=(evidence,),
        )


class SelfProvider(EvidenceProvider):
    """Observe Thrilla's local repository and identity."""

    _TERMS = (
        "what version are you",
        "what version is thrilla",
        "thrilla version",
        "what branch are you",
        "which branch are you",
        "what branch is thrilla",
        "what commit are you",
        "which commit are you",
        "what commit is thrilla",
        "repository clean",
        "repo clean",
        "repository dirty",
        "repo dirty",
        "where is your repository",
        "where is your repo",
        "where is thrilla",
        "what project are you",
        "current code state",
        "repository state",
        "repo state",
        "git status",
    )

    def __init__(
        self,
        repo_root: str,
        version: str,
        run_fn: Optional[
            Callable[..., str]
        ] = None,
    ) -> None:
        self.repo_root = repo_root
        self.version = version

        self._run_fn = (
            run_fn
            if run_fn is not None
            else self._run_git
        )

    def supports(
        self,
        prompt: str,
    ) -> bool:
        lowered = prompt.lower()

        return any(
            term in lowered
            for term in self._TERMS
        )

    @staticmethod
    def _run_git(
        args,
        cwd: str,
    ) -> str:
        import subprocess

        completed = subprocess.run(
            [
                "git",
                *args,
            ],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

        return completed.stdout.strip()

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        del prompt

        root = self._run_fn(
            (
                "rev-parse",
                "--show-toplevel",
            ),
            self.repo_root,
        ).strip()

        branch = self._run_fn(
            (
                "branch",
                "--show-current",
            ),
            self.repo_root,
        ).strip()

        commit = self._run_fn(
            (
                "rev-parse",
                "HEAD",
            ),
            self.repo_root,
        ).strip()

        message = self._run_fn(
            (
                "log",
                "-1",
                "--pretty=%s",
            ),
            self.repo_root,
        ).strip()

        status = self._run_fn(
            (
                "status",
                "--porcelain",
            ),
            self.repo_root,
        )

        changed_paths = len(
            [
                line
                for line in status.splitlines()
                if line.strip()
            ]
        )

        clean = (
            changed_paths == 0
        )

        if not branch:
            branch = "(detached HEAD)"

        version = (
            str(self.version).strip()
            or "unknown"
        )

        answer = (
            "Project: THRILLA-ZILLA\n"
            "Version: {version}\n"
            "Repository root: {root}\n"
            "Branch: {branch}\n"
            "HEAD: {commit} {message}\n"
            "Worktree clean: {clean}\n"
            "Changed paths: {changed_paths}"
        ).format(
            version=version,
            root=root,
            branch=branch,
            commit=commit,
            message=message,
            clean=(
                "yes"
                if clean
                else "no"
            ),
            changed_paths=changed_paths,
        )

        evidence = Evidence(
            source="repository_state",
            detail=(
                "Observed from the local Git repository "
                "using read-only Git commands and the "
                "configured Thrilla version."
            ),
            content=answer,
        )

        return AnswerContext(
            direct_answer=answer,
            evidence=(evidence,),
        )


class MemoryProvider(EvidenceProvider):
    """Retrieve relevant durable local conversation history."""

    _TERMS = (
        "what did i say",
        "what have i said",
        "do you remember",
        "did i tell you",
        "remember when",
        "what did we talk",
        "what have we talked",
        "what were we talking",
        "earlier conversation",
        "previous conversation",
        "previously discussed",
        "from earlier",
    )

    _STOPWORDS = {
        "a",
        "about",
        "an",
        "and",
        "are",
        "before",
        "did",
        "do",
        "earlier",
        "from",
        "have",
        "i",
        "is",
        "it",
        "me",
        "my",
        "of",
        "our",
        "previous",
        "previously",
        "remember",
        "say",
        "said",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "talk",
        "talked",
        "was",
        "we",
        "were",
        "what",
        "when",
        "you",
    }

    def __init__(
        self,
        records_fn: Callable[..., list],
        max_records: int = 200,
        max_matches: int = 6,
    ) -> None:
        self._records_fn = records_fn
        self.max_records = max(
            1,
            int(max_records),
        )
        self.max_matches = max(
            1,
            int(max_matches),
        )

    def supports(
        self,
        prompt: str,
    ) -> bool:
        lowered = prompt.lower()

        return any(
            term in lowered
            for term in self._TERMS
        )

    @classmethod
    def _tokens(
        cls,
        value: str,
    ):
        import re

        return {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                value.lower(),
            )
            if len(token) > 1
            and token not in cls._STOPWORDS
        }

    @staticmethod
    def _normalized(
        value: str,
    ) -> str:
        return " ".join(
            value.lower().split()
        )

    def _candidate_records(
        self,
        prompt: str,
    ):
        records = list(
            self._records_fn(
                limit=self.max_records
            )
        )

        # ask() persists the owner's current prompt before
        # provider resolution. Exclude that final record so
        # Thrilla never "remembers" the question it is
        # currently answering as prior history.
        if records:
            last = records[-1]

            if (
                last.get("role") == "user"
                and self._normalized(
                    str(
                        last.get(
                            "content",
                            "",
                        )
                    )
                )
                == self._normalized(prompt)
            ):
                records = records[:-1]

        return records

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        records = self._candidate_records(
            prompt
        )

        query_tokens = self._tokens(
            prompt
        )

        ranked = []

        for index, record in enumerate(
            records
        ):
            role = record.get("role")

            content = record.get(
                "content"
            )

            if (
                role not in {
                    "user",
                    "assistant",
                }
                or not isinstance(
                    content,
                    str,
                )
                or not content.strip()
            ):
                continue

            if query_tokens:
                overlap = (
                    query_tokens
                    & self._tokens(content)
                )

                score = len(overlap)

                if score == 0:
                    continue
            else:
                score = 0

            ranked.append(
                (
                    score,
                    index,
                    record,
                )
            )

        if query_tokens:
            ranked.sort(
                key=lambda item: (
                    item[0],
                    item[1],
                ),
                reverse=True,
            )
        else:
            ranked.sort(
                key=lambda item: item[1],
                reverse=True,
            )

        matches = [
            item[2]
            for item in ranked[
                : self.max_matches
            ]
        ]

        if not matches:
            return AnswerContext(
                gap=KnowledgeGap(
                    unknown=(
                        "matching prior conversation"
                    ),
                    missing_evidence=(
                        "relevant local conversation history",
                    ),
                    reason=(
                        "No matching conversation history "
                        "was found in Thrilla's local "
                        "conversation store."
                    ),
                    resolution=(
                        "provide more specific recall terms",
                        (
                            "confirm the conversation was "
                            "saved locally"
                        ),
                    ),
                )
            )

        lines = [
            "Relevant local conversation history:"
        ]

        for number, record in enumerate(
            matches,
            start=1,
        ):
            role = record.get(
                "role",
                "unknown",
            )

            timestamp = record.get(
                "timestamp",
                "unknown time",
            )

            route = record.get(
                "route"
            )

            header = (
                "{0}. [{1}] {2}".format(
                    number,
                    role,
                    timestamp,
                )
            )

            if route:
                header += (
                    " route={0}".format(
                        route
                    )
                )

            lines.extend(
                [
                    header,
                    str(
                        record.get(
                            "content",
                            "",
                        )
                    ),
                ]
            )

        answer = "\n".join(lines)

        evidence = Evidence(
            source=(
                "local_conversation_history"
            ),
            detail=(
                "Retrieved from Thrilla's durable local "
                "conversation history as evidence only. "
                "The owner's current request remains "
                "authoritative."
            ),
            content=answer,
        )

        return AnswerContext(
            direct_answer=answer,
            evidence=(evidence,),
        )
