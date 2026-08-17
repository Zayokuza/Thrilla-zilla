"""Read-only observation providers for Universal Ask."""

from datetime import datetime
from typing import Callable, Optional

from .answers import (
    AnswerContext,
    Evidence,
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
