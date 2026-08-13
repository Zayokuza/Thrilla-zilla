"""Local conversation history with atomic clear and bounded model context."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ConversationHistory:
    def __init__(self, state_root: Path) -> None:
        self.path = state_root / "conversation.jsonl"

    def append(self, role: str, content: str, route: Optional[str] = None) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Conversation role must be user or assistant.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if route:
            record["route"] = route
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def records(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        if limit is not None:
            bounded = max(0, limit)
            lines = lines[-bounded:] if bounded else []
        output: List[Dict[str, str]] = []
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("role") in {"user", "assistant"} and isinstance(record.get("content"), str):
                output.append(record)
        return output

    def messages(self, turns: int = 12) -> List[Dict[str, str]]:
        records = self.records(limit=max(0, turns) * 2)
        return [
            {"role": record["role"], "content": record["content"]}
            for record in records
        ]

    def clear(self) -> bool:
        if not self.path.exists():
            return False
        cleared = self.path.with_name("conversation.cleared.jsonl")
        suffix = 1
        while cleared.exists():
            cleared = self.path.with_name(f"conversation.cleared.{suffix}.jsonl")
            suffix += 1
        self.path.replace(cleared)
        return True
