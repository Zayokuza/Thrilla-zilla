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


# ==================================================================
# Stage 2 complete release-management core
# ==================================================================

import os
import subprocess
import sys
from contextlib import AbstractContextManager
from typing import List


CURRENT_POINTER = "current"
PREVIOUS_POINTER = "previous"
LOCK_NAME = "update.lock"


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value.rstrip("\n") + "\n", encoding="utf-8")
    os.replace(str(temporary), str(path))


def _read_pointer(state_root: Path, name: str) -> Optional[str]:
    path = Path(state_root).expanduser().resolve() / name
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    return value or None


def current_release(state_root: Path) -> Optional[str]:
    return _read_pointer(state_root, CURRENT_POINTER)


def previous_release(state_root: Path) -> Optional[str]:
    return _read_pointer(state_root, PREVIOUS_POINTER)


def _release_dir(state_root: Path, release_id: str) -> Path:
    return (
        Path(state_root).expanduser().resolve()
        / "releases"
        / _safe_token(release_id)
    )


def _load_manifest(release_dir: Path) -> Dict[str, object]:
    manifest_path = release_dir / "release.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as error:
        raise ReleaseStageError(
            f"Invalid release manifest: {manifest_path}: {error}"
        ) from error

    if not isinstance(payload, dict):
        raise ReleaseStageError(
            f"Release manifest must be an object: {manifest_path}"
        )
    return payload


def _write_manifest(
    manifest_path: Path,
    payload: Dict[str, object],
) -> None:
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(str(temporary), str(manifest_path))


def _run_checked(
    command: List[str],
    cwd: Path,
    environment: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        output = result.stdout.strip()
        raise ReleaseStageError(
            "Release verification command failed "
            f"(exit {result.returncode}): {' '.join(command)}"
            + (f"\n{output}" if output else "")
        )

    return result


def validate_release(
    plan: ReleasePlan,
    python_executable: str = sys.executable,
) -> Dict[str, object]:
    """Compile and test a staged candidate before activation."""
    payload = plan.payload_dir.resolve()

    if not payload.is_dir():
        raise ReleaseStageError(
            f"Release payload does not exist: {payload}"
        )

    manifest = _load_manifest(plan.release_dir)

    environment = os.environ.copy()
    old_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(payload)
        if not old_pythonpath
        else str(payload) + os.pathsep + old_pythonpath
    )

    try:
        _run_checked(
            [
                python_executable,
                "-m",
                "compileall",
                "-q",
                str(payload / "thrilla"),
            ],
            payload,
            environment,
        )
        compile_passed = True

        _run_checked(
            [
                python_executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(payload / "tests"),
                "-q",
            ],
            payload,
            environment,
        )
        tests_passed = True

    except ReleaseStageError:
        manifest["status"] = "validation-failed"
        manifest["tests_executed"] = True
        manifest["validated"] = False
        _write_manifest(plan.manifest_path, manifest)
        raise

    manifest.update(
        {
            "status": "validated",
            "tests_executed": True,
            "compile_passed": compile_passed,
            "tests_passed": tests_passed,
            "validated": True,
            "activation_supported": True,
            "rollback_supported": True,
        }
    )
    _write_manifest(plan.manifest_path, manifest)

    return manifest


def _startup_proof(
    release_dir: Path,
    python_executable: str,
) -> None:
    payload = release_dir / "payload"

    environment = os.environ.copy()
    old_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        str(payload)
        if not old_pythonpath
        else str(payload) + os.pathsep + old_pythonpath
    )

    _run_checked(
        [python_executable, "-m", "thrilla", "--version"],
        payload,
        environment,
    )


def activate_release(
    plan: ReleasePlan,
    python_executable: str = sys.executable,
) -> Dict[str, object]:
    """Atomically activate a validated candidate with recovery."""
    manifest = _load_manifest(plan.release_dir)

    if manifest.get("validated") is not True:
        raise ReleaseStageError(
            f"Release is not validated: {plan.release_id}"
        )

    state = plan.state_root.resolve()
    current_path = state / CURRENT_POINTER
    previous_path = state / PREVIOUS_POINTER

    old_current = current_release(state)
    old_previous = previous_release(state)

    if old_current:
        _atomic_write_text(
            previous_path,
            old_current,
        )
    else:
        try:
            previous_path.unlink()
        except FileNotFoundError:
            pass

    _atomic_write_text(
        current_path,
        plan.release_id,
    )

    try:
        _startup_proof(
            plan.release_dir,
            python_executable,
        )

    except Exception as error:
        if old_current:
            _atomic_write_text(
                current_path,
                old_current,
            )
        else:
            try:
                current_path.unlink()
            except FileNotFoundError:
                pass

        if old_previous:
            _atomic_write_text(
                previous_path,
                old_previous,
            )
        else:
            try:
                previous_path.unlink()
            except FileNotFoundError:
                pass

        manifest["status"] = "activation-failed"
        _write_manifest(
            plan.manifest_path,
            manifest,
        )

        raise ReleaseStageError(
            f"Activation proof failed for {plan.release_id}; "
            "the prior release state was restored."
        ) from error

    manifest["status"] = "active"
    manifest["launcher_modified"] = False
    _write_manifest(
        plan.manifest_path,
        manifest,
    )

    if old_current and old_current != plan.release_id:
        old_dir = _release_dir(
            state,
            old_current,
        )

        if old_dir.is_dir():
            try:
                old_manifest = _load_manifest(
                    old_dir
                )
                old_manifest["status"] = "previous"
                _write_manifest(
                    old_dir / "release.json",
                    old_manifest,
                )
            except ReleaseStageError:
                # The new verified release remains authoritative.
                pass

    return manifest


def _rollback_release_unlocked(
    state_root: Path,
    python_executable: str = sys.executable,
) -> str:
    """Swap current and previous releases after proving previous can start."""
    state = Path(state_root).expanduser().resolve()

    current_id = current_release(state)
    previous_id = previous_release(state)

    if not previous_id:
        raise ReleaseStageError(
            "No previous release is available for rollback."
        )

    target_dir = _release_dir(state, previous_id)

    if not target_dir.is_dir():
        raise ReleaseStageError(
            f"Previous release directory is missing: {target_dir}"
        )

    _startup_proof(target_dir, python_executable)

    _atomic_write_text(state / CURRENT_POINTER, previous_id)

    if current_id:
        _atomic_write_text(state / PREVIOUS_POINTER, current_id)

    target_manifest = _load_manifest(target_dir)
    target_manifest["status"] = "active"
    _write_manifest(target_dir / "release.json", target_manifest)

    if current_id:
        old_dir = _release_dir(state, current_id)
        if old_dir.is_dir():
            old_manifest = _load_manifest(old_dir)
            old_manifest["status"] = "previous"
            _write_manifest(old_dir / "release.json", old_manifest)

    return previous_id


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


class UpdateLock(AbstractContextManager):
    """Exclusive release-mutation lock with stale-owner recovery."""

    def __init__(self, state_root: Path) -> None:
        self.state_root = Path(state_root).expanduser().resolve()
        self.path = self.state_root / LOCK_NAME
        self.file_descriptor: Optional[int] = None

    def _existing_owner(self) -> Optional[int]:
        try:
            value = self.path.read_text(
                encoding="utf-8"
            ).strip()
        except (FileNotFoundError, OSError):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _open_exclusive(self) -> int:
        return os.open(
            str(self.path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )

    def __enter__(self):
        self.state_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            self.file_descriptor = self._open_exclusive()

        except FileExistsError:
            owner = self._existing_owner()

            if owner is not None and _pid_is_alive(owner):
                raise ReleaseStageError(
                    "Another Thrilla release operation "
                    f"is active with PID {owner}: {self.path}"
                )

            # Dead/invalid owner: remove only the stale lock and
            # attempt the atomic create once more.
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass

            try:
                self.file_descriptor = self._open_exclusive()
            except FileExistsError as error:
                raise ReleaseStageError(
                    "Another Thrilla release operation "
                    f"acquired the lock: {self.path}"
                ) from error

        os.write(
            self.file_descriptor,
            f"{os.getpid()}\n".encode("ascii"),
        )

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        if self.file_descriptor is not None:
            os.close(self.file_descriptor)
            self.file_descriptor = None

        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

        return False


# ==================================================================
# Stage 2 stable release workflow
# ==================================================================

def install_release(
    project_root: Path,
    state_root: Path,
    commit: str,
    timestamp: Optional[str] = None,
    python_executable: str = sys.executable,
) -> Dict[str, object]:
    """Stage, validate and atomically activate one local release."""
    state = Path(state_root).expanduser().resolve()

    with UpdateLock(state):
        plan = build_plan(
            project_root,
            state,
            commit,
            timestamp=timestamp,
        )

        stage_candidate(plan)
        validate_release(
            plan,
            python_executable=python_executable,
        )

        return activate_release(
            plan,
            python_executable=python_executable,
        )


def release_status(state_root: Path) -> Dict[str, object]:
    """Return the complete local release inventory."""
    state = Path(state_root).expanduser().resolve()
    releases_root = state / "releases"

    records = []

    if releases_root.is_dir():
        for release_dir in sorted(
            releases_root.iterdir(),
            key=lambda item: item.name,
        ):
            if not release_dir.is_dir():
                continue

            try:
                manifest = _load_manifest(release_dir)
                status = manifest.get("status", "unknown")
                commit = manifest.get("commit")
            except ReleaseStageError:
                status = "invalid-manifest"
                commit = None

            records.append(
                {
                    "release_id": release_dir.name,
                    "status": status,
                    "commit": commit,
                    "path": str(release_dir),
                }
            )

    return {
        "state_root": str(state),
        "current": current_release(state),
        "previous": previous_release(state),
        "releases": records,
    }


def _prune_releases_unlocked(
    state_root: Path,
    keep_newest: int = 5,
):
    """Remove old inactive releases while always protecting current/previous."""
    if keep_newest < 0:
        raise ReleaseStageError(
            "keep_newest cannot be negative."
        )

    state = Path(state_root).expanduser().resolve()
    releases_root = state / "releases"

    if not releases_root.is_dir():
        return []

    protected = {
        value
        for value in (
            current_release(state),
            previous_release(state),
        )
        if value
    }

    release_dirs = sorted(
        (
            item
            for item in releases_root.iterdir()
            if item.is_dir()
        ),
        key=lambda item: item.name,
        reverse=True,
    )

    newest = {
        item.name
        for item in release_dirs[:keep_newest]
    }

    keep = protected | newest
    removed = []

    for release_dir in release_dirs:
        if release_dir.name in keep:
            continue

        shutil.rmtree(release_dir)
        removed.append(release_dir.name)

    return removed


def write_posix_launcher(
    launcher_path: Path,
    state_root: Path,
    python_executable: str = "python",
) -> Path:
    """Write a stable POSIX launcher that follows the active release pointer."""
    launcher = Path(launcher_path).expanduser().absolute()
    state = str(Path(state_root).expanduser().resolve())

    launcher.parent.mkdir(parents=True, exist_ok=True)

    script = f'''#!/usr/bin/env bash
set -eu

state_default={state!r}
python_default={str(python_executable)!r}

state_root="${{THRILLA_STATE_ROOT:-$state_default}}"
python_bin="${{THRILLA_PYTHON:-$python_default}}"

if [ -z "${{THRILLA_HOME:-}}" ]; then
    export THRILLA_HOME="$state_root"
fi

current_file="$state_root/current"

if [ ! -f "$current_file" ]; then
    echo "Thrilla has no active release." >&2
    exit 1
fi

release_id="$(tr -d '\\r\\n' < "$current_file")"

case "$release_id" in
    ""|*[!A-Za-z0-9._-]*)
        echo "Thrilla active release pointer is invalid." >&2
        exit 1
        ;;
esac

payload="$state_root/releases/$release_id/payload"

if [ ! -d "$payload/thrilla" ]; then
    echo "Thrilla active release payload is missing: $payload" >&2
    exit 1
fi

cd "$payload"

if [ -n "${{PYTHONPATH:-}}" ]; then
    export PYTHONPATH="$payload:$PYTHONPATH"
else
    export PYTHONPATH="$payload"
fi

exec "$python_bin" -m thrilla "$@"
'''

    temporary = launcher.with_name(
        launcher.name + ".tmp"
    )

    temporary.write_text(
        script,
        encoding="utf-8",
    )
    temporary.chmod(0o755)
    os.replace(str(temporary), str(launcher))
    launcher.chmod(0o755)

    return launcher


def write_windows_launcher(
    launcher_path: Path,
    state_root: Path,
    python_executable: str = "python",
) -> Path:
    """Write the Windows stable launcher using the same current pointer."""
    launcher = Path(launcher_path).expanduser().absolute()
    state = str(Path(state_root).expanduser().resolve())

    launcher.parent.mkdir(parents=True, exist_ok=True)

    contents = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'if not defined THRILLA_STATE_ROOT '
        f'set "THRILLA_STATE_ROOT={state}"\r\n'
        f'if not defined THRILLA_PYTHON '
        f'set "THRILLA_PYTHON={python_executable}"\r\n'
        'if not defined THRILLA_HOME '
        'set "THRILLA_HOME=%THRILLA_STATE_ROOT%"\r\n'
        'if not exist "%THRILLA_STATE_ROOT%\\current" (\r\n'
        '  echo Thrilla has no active release. 1>&2\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        'set /p THRILLA_RELEASE=<"%THRILLA_STATE_ROOT%\\current"\r\n'
        'set "THRILLA_PAYLOAD=%THRILLA_STATE_ROOT%\\releases\\'
        '%THRILLA_RELEASE%\\payload"\r\n'
        'if not exist "%THRILLA_PAYLOAD%\\thrilla" (\r\n'
        '  echo Thrilla active release payload is missing. 1>&2\r\n'
        "  exit /b 1\r\n"
        ")\r\n"
        'pushd "%THRILLA_PAYLOAD%"\r\n'
        'set "PYTHONPATH=%THRILLA_PAYLOAD%;%PYTHONPATH%"\r\n'
        '"%THRILLA_PYTHON%" -m thrilla %*\r\n'
        'set "THRILLA_EXIT=%ERRORLEVEL%"\r\n'
        'popd\r\n'
        'exit /b %THRILLA_EXIT%\r\n'
    )

    temporary = launcher.with_name(
        launcher.name + ".tmp"
    )

    temporary.write_text(
        contents,
        encoding="utf-8",
        newline="",
    )

    os.replace(str(temporary), str(launcher))

    return launcher



def rollback_release(
    state_root: Path,
    python_executable: str = sys.executable,
) -> str:
    """Atomically roll back while excluding concurrent release mutations."""
    state = Path(state_root).expanduser().resolve()

    with UpdateLock(state):
        return _rollback_release_unlocked(
            state,
            python_executable=python_executable,
        )


def prune_releases(
    state_root: Path,
    keep_newest: int = 5,
):
    """Prune inactive releases under the exclusive release lock."""
    state = Path(state_root).expanduser().resolve()

    with UpdateLock(state):
        return _prune_releases_unlocked(
            state,
            keep_newest=keep_newest,
        )
