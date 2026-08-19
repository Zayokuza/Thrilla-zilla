"""Local conversation history with cached bounded model context."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ConversationHistory:
    """Persist JSONL while keeping the active-process read path in RAM."""

    def __init__(self, state_root: Path) -> None:
        self.path = state_root / "conversation.jsonl"
        self._cache: Optional[List[Dict[str, str]]] = None

    @staticmethod
    def _valid(record):
        return (
            record.get("role")
            in {
                "user",
                "assistant",
            }
            and isinstance(
                record.get("content"),
                str,
            )
        )

    def _load(self) -> List[Dict[str, str]]:
        if self._cache is not None:
            return self._cache

        output = []

        try:
            handle = self.path.open(
                "r",
                encoding="utf-8",
            )
        except OSError:
            self._cache = []
            return self._cache

        with handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if self._valid(record):
                    output.append(record)

        self._cache = output
        return self._cache

    def append(
        self,
        role: str,
        content: str,
        route: Optional[str] = None,
    ) -> None:
        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Conversation role must be user or assistant."
            )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        record = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "role": role,
            "content": content,
        }

        if route:
            record["route"] = route

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

        if self._cache is not None:
            self._cache.append(record)

    def records(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        records = self._load()

        if limit is None:
            selected = records
        else:
            bounded = max(0, int(limit))
            selected = (
                records[-bounded:]
                if bounded
                else []
            )

        return [
            dict(record)
            for record in selected
        ]

    def messages(
        self,
        turns: Optional[int] = 12,
    ) -> List[Dict[str, str]]:
        limit = (
            None
            if turns is None
            else max(0, turns) * 2
        )

        records = self.records(
            limit=limit
        )

        return [
            {
                "role": record["role"],
                "content": record["content"],
            }
            for record in records
        ]

    def reload(self) -> None:
        """Explicitly invalidate the in-process cache."""

        self._cache = None

    def clear(self) -> bool:
        if not self.path.exists():
            self._cache = []
            return False

        cleared = self.path.with_name(
            "conversation.cleared.jsonl"
        )
        suffix = 1

        while cleared.exists():
            cleared = self.path.with_name(
                "conversation.cleared.{0}.jsonl".format(
                    suffix
                )
            )
            suffix += 1

        self.path.replace(cleared)
        self._cache = []
        return True
