"""Inactive Stage-2 release candidate staging.

This module intentionally does NOT activate releases, modify launchers,
perform rollback, or run automatically during normal Thrilla startup.

It provides only the first safe building blocks for future atomic updates:
dated release directories, isolated source copies, and candidate manifests.
"""

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


class ReleaseStageError(RuntimeError):
    """Raised when an inactive release candidate cannot be staged safely."""


@dataclass(frozen=True)
class ReleasePlan:
    project_root: Path
    state_root: Path
    commit: str
    timestamp: str
    release_id: str
    release_dir: Path
    payload_dir: Path
    manifest_path: Path


def _safe_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-")
    if not cleaned:
        raise ReleaseStageError("Release token cannot be empty.")
    return cleaned


def build_plan(
    project_root: Path,
    state_root: Path,
    commit: str,
    timestamp: Optional[str] = None,
) -> ReleasePlan:
    """Create an inactive release layout without touching the filesystem."""
    source = Path(project_root).expanduser().resolve()
    state = Path(state_root).expanduser().resolve()

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    safe_timestamp = _safe_token(timestamp)
    safe_commit = _safe_token(commit)[:12]

    release_id = f"{safe_timestamp}-{safe_commit}"
    release_dir = state / "releases" / release_id

    return ReleasePlan(
        project_root=source,
        state_root=state,
        commit=str(commit),
        timestamp=safe_timestamp,
        release_id=release_id,
        release_dir=release_dir,
        payload_dir=release_dir / "payload",
        manifest_path=release_dir / "release.json",
    )


def _ignore_source(directory: str, names):
    ignored = set()

    blocked_names = {
        ".git",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "__pycache__",
    }

    for name in names:
        if name in blocked_names or name.endswith(".pyc"):
            ignored.add(name)

    return ignored


def stage_candidate(plan: ReleasePlan) -> Dict[str, object]:
    """Copy a candidate into an isolated dated directory.

    This function deliberately stops before validation or activation.
    """
    if plan.release_dir.exists():
        raise ReleaseStageError(
            f"Release already exists and will not be overwritten: "
            f"{plan.release_dir}"
        )

    if not plan.project_root.is_dir():
        raise ReleaseStageError(
            f"Project root does not exist: {plan.project_root}"
        )

    if not (plan.project_root / "thrilla").is_dir():
        raise ReleaseStageError(
            f"Thrilla package was not found under {plan.project_root}"
        )

    plan.release_dir.mkdir(parents=True, exist_ok=False)

    try:
        shutil.copytree(
            plan.project_root,
            plan.payload_dir,
            ignore=_ignore_source,
        )

        manifest: Dict[str, object] = {
            "schema": 1,
            "release_id": plan.release_id,
            "timestamp": plan.timestamp,
            "commit": plan.commit,
            "source": str(plan.project_root),
            "payload": str(plan.payload_dir.resolve()),
            "status": "staged-inactive",

            # These remain explicitly false until later Stage-2 work.
            "tests_executed": False,
            "activation_supported": False,
            "rollback_supported": False,
            "launcher_modified": False,
        }

        temporary = plan.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(plan.manifest_path)

        return manifest

    except Exception:
        # Candidate creation is isolated from the active Thrilla installation.
        # If staging fails, remove only the incomplete candidate directory.
        shutil.rmtree(plan.release_dir, ignore_errors=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage an inactive Thrilla release candidate."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Thrilla source repository to copy",
    )
    parser.add_argument(
        "--state-root",
        default=str(Path.home() / ".thrilla-zilla"),
        help="Thrilla state directory",
    )
    parser.add_argument(
        "--commit",
        required=True,
        help="Git commit or source identifier",
    )
    parser.add_argument(
        "--timestamp",
        help="Optional fixed YYYYMMDD-HHMMSS style identifier",
    )

    arguments = parser.parse_args(argv)

    plan = build_plan(
        Path(arguments.project_root),
        Path(arguments.state_root),
        arguments.commit,
        timestamp=arguments.timestamp,
    )

    manifest = stage_candidate(plan)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
