"""Durable file checkpoints for Thrilla repository edits."""

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple


class CheckpointError(RuntimeError):
    """Checkpoint creation or restoration failed."""


@dataclass(frozen=True)
class CheckpointEntry:
    relative_path: str
    existed: bool
    mode: int
    snapshot_name: str


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    directory: Path
    entries: Tuple[CheckpointEntry, ...]


class CheckpointManager:
    """Snapshot only explicitly targeted repository files."""

    def __init__(self, repo_root: Path, state_root: Path) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.state_root = Path(state_root).expanduser().resolve()
        self.base = self.state_root / "checkpoints" / "coding"

    def _resolve_relative(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise CheckpointError("checkpoint path must be a non-empty string")
        relative = Path(value)
        if relative.is_absolute():
            raise CheckpointError("checkpoint paths must be repository-relative")
        candidate = (self.repo_root / relative).resolve()
        if candidate == self.repo_root or self.repo_root not in candidate.parents:
            raise CheckpointError("checkpoint path escapes repository root")
        if ".git" in candidate.relative_to(self.repo_root).parts:
            raise CheckpointError("checkpoint may not target .git")
        return candidate

    def create(self, relative_paths: Iterable[str]) -> Checkpoint:
        normalized = []
        seen = set()
        for value in relative_paths:
            candidate = self._resolve_relative(value)
            relative = str(candidate.relative_to(self.repo_root))
            if relative in seen:
                continue
            seen.add(relative)
            normalized.append((relative, candidate))
        if not normalized:
            raise CheckpointError("checkpoint requires at least one target file")

        checkpoint_id = "{}-{}".format(
            time.strftime("%Y%m%d-%H%M%S"),
            uuid.uuid4().hex[:10],
        )
        directory = self.base / checkpoint_id
        files_dir = directory / "files"
        files_dir.mkdir(parents=True, exist_ok=False)
        entries = []

        try:
            for index, (relative, candidate) in enumerate(normalized):
                existed = candidate.exists()
                mode = 0
                snapshot_name = ""
                if existed:
                    if not candidate.is_file():
                        raise CheckpointError(
                            "checkpoint target is not a regular file: {}".format(relative)
                        )
                    mode = candidate.stat().st_mode & 0o777
                    snapshot_name = "{:03d}.bin".format(index)
                    shutil.copyfile(candidate, files_dir / snapshot_name)
                entries.append(
                    CheckpointEntry(
                        relative_path=relative,
                        existed=existed,
                        mode=mode,
                        snapshot_name=snapshot_name,
                    )
                )

            (directory / "manifest.json").write_text(
                json.dumps(
                    {
                        "checkpoint_id": checkpoint_id,
                        "repo_root": str(self.repo_root),
                        "created_at": time.time(),
                        "entries": [
                            {
                                "relative_path": entry.relative_path,
                                "existed": entry.existed,
                                "mode": entry.mode,
                                "snapshot_name": entry.snapshot_name,
                            }
                            for entry in entries
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

        return Checkpoint(checkpoint_id, directory, tuple(entries))

    def rollback(self, checkpoint: Checkpoint) -> None:
        files_dir = checkpoint.directory / "files"
        for entry in checkpoint.entries:
            target = self._resolve_relative(entry.relative_path)
            if entry.existed:
                snapshot = files_dir / entry.snapshot_name
                if not snapshot.is_file():
                    raise CheckpointError("checkpoint snapshot missing: {}".format(snapshot))
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".thrilla-rollback-tmp")
                shutil.copyfile(snapshot, temporary)
                os.replace(temporary, target)
                if entry.mode:
                    os.chmod(target, entry.mode)
            elif target.exists():
                if not target.is_file():
                    raise CheckpointError("rollback refuses to remove non-file target")
                target.unlink()
