"""Minimal privacy-aware activity logging."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class AuditLog:
    def __init__(self, state_root: Path) -> None:
        self.path = state_root / "activity.jsonl"

    def write(self, event: str, **fields: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        record.update(fields)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")

    def tail(self, count: int = 20) -> List[Dict[str, Any]]:
        try:
            all_lines = self.path.read_text(encoding="utf-8").splitlines()
            bounded = max(0, count)
            lines = all_lines[-bounded:] if bounded else []
        except OSError:
            return []
        records: List[Dict[str, Any]] = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records
