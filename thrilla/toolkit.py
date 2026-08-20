"""Expanded bounded local tools for Thrilla Stage 7B."""

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from .tools import (
    ToolPermission,
    ToolRegistry,
    ToolSpec,
)


class Stage7ToolFactory:
    """Additional local capabilities built on Thrilla's root guard."""

    def __init__(
        self,
        local_factory,
        repo_root: Path,
    ) -> None:
        self.local = local_factory
        self.repo_root = (
            Path(repo_root)
            .expanduser()
            .resolve()
        )

    def _cwd(
        self,
        value: Any,
    ) -> Path:
        path = self.local._path(
            str(
                value
                if value is not None
                else self.repo_root
            )
        )

        if not path.is_dir():
            raise NotADirectoryError(str(path))

        return path

    @staticmethod
    def _timeout(
        value: Any,
        *,
        default: float = 20.0,
        maximum: float = 180.0,
    ) -> float:
        return max(
            0.1,
            min(
                float(
                    default
                    if value is None
                    else value
                ),
                maximum,
            ),
        )

    @staticmethod
    def _run(
        argv,
        cwd: Path,
        timeout: float,
        max_chars: int = 30000,
    ):
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=timeout,
            check=False,
        )

        return {
            "source": "process:{0}".format(
                Path(argv[0]).name
            ),
            "detail": (
                "process exited with code {0}"
            ).format(
                completed.returncode
            ),
            "argv": list(argv),
            "cwd": str(cwd),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-max_chars:],
            "stderr": completed.stderr[-max_chars:],
        }

    def file_stat(
        self,
        args: Mapping[str, Any],
    ):
        path = self.local._path(
            args.get("path")
        )

        stat = path.stat()

        if path.is_dir():
            kind = "directory"
        elif path.is_file():
            kind = "file"
        elif path.is_symlink():
            kind = "symlink"
        else:
            kind = "other"

        return {
            "source": str(path),
            "detail": (
                "observed local filesystem metadata"
            ),
            "type": kind,
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "mode": oct(stat.st_mode & 0o7777),
        }

    def file_glob(
        self,
        args: Mapping[str, Any],
    ):
        root = self.local._path(
            args.get("path")
        )

        if not root.is_dir():
            raise NotADirectoryError(
                str(root)
            )

        pattern = args.get("pattern")

        if (
            not isinstance(pattern, str)
            or not pattern.strip()
        ):
            raise ValueError(
                "pattern must be a non-empty string"
            )

        if "\x00" in pattern:
            raise ValueError(
                "glob pattern contains NUL"
            )

        max_matches = max(
            1,
            min(
                int(
                    args.get(
                        "max_matches",
                        100,
                    )
                ),
                1000,
            ),
        )

        matches = []

        for candidate in root.glob(pattern):
            resolved = candidate.resolve()

            # Re-apply Thrilla's root guard to every expansion so a
            # pattern containing .. cannot escape an authorized root.
            try:
                self.local._path(
                    str(resolved)
                )
            except PermissionError:
                continue

            matches.append(
                {
                    "path": str(resolved),
                    "type": (
                        "directory"
                        if resolved.is_dir()
                        else "file"
                    ),
                }
            )

            if len(matches) >= max_matches:
                break

        matches.sort(
            key=lambda item: item["path"]
        )

        return {
            "source": str(root),
            "detail": (
                "glob matched {0} paths"
            ).format(len(matches)),
            "pattern": pattern,
            "matches": matches,
            "truncated": (
                len(matches) >= max_matches
            ),
        }

    def file_hash(
        self,
        args: Mapping[str, Any],
    ):
        path = self.local._path(
            args.get("path")
        )

        if not path.is_file():
            raise FileNotFoundError(
                str(path)
            )

        max_bytes = max(
            1,
            min(
                int(
                    args.get(
                        "max_bytes",
                        64 * 1024 * 1024,
                    )
                ),
                512 * 1024 * 1024,
            ),
        )

        size = path.stat().st_size

        if size > max_bytes:
            raise ValueError(
                "file exceeds configured hash byte limit"
            )

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(chunk)

        return {
            "source": str(path),
            "detail": (
                "computed SHA-256 for {0} bytes"
            ).format(size),
            "size": int(size),
            "sha256": digest.hexdigest(),
        }

    def process_which(
        self,
        args: Mapping[str, Any],
    ):
        name = args.get("name")

        if (
            not isinstance(name, str)
            or not name.strip()
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if (
            "/" in name
            or "\\" in name
        ):
            raise ValueError(
                "name must be an executable basename"
            )

        located = shutil.which(
            name.strip()
        )

        return {
            "source": "local-path",
            "detail": (
                "resolved executable"
                if located
                else "executable not found"
            ),
            "name": name.strip(),
            "path": located or "",
        }

    def git_status(
        self,
        args: Mapping[str, Any],
    ):
        cwd = self._cwd(
            args.get("cwd")
        )

        return self._run(
            (
                "git",
                "status",
                "--short",
                "--branch",
            ),
            cwd,
            self._timeout(
                args.get("timeout"),
                maximum=30.0,
            ),
        )

    def git_diff(
        self,
        args: Mapping[str, Any],
    ):
        cwd = self._cwd(
            args.get("cwd")
        )

        staged = bool(
            args.get(
                "staged",
                False,
            )
        )

        argv = [
            "git",
            "diff",
            "--no-ext-diff",
        ]

        if staged:
            argv.append("--cached")

        return self._run(
            argv,
            cwd,
            self._timeout(
                args.get("timeout"),
                maximum=30.0,
            ),
            max_chars=max(
                1000,
                min(
                    int(
                        args.get(
                            "max_chars",
                            30000,
                        )
                    ),
                    100000,
                ),
            ),
        )

    def python_unittest(
        self,
        args: Mapping[str, Any],
    ):
        cwd = self._cwd(
            args.get("cwd")
        )

        mode = str(
            args.get(
                "mode",
                "discover",
            )
        ).strip().lower()

        timeout = self._timeout(
            args.get("timeout"),
            default=60.0,
            maximum=180.0,
        )

        if mode == "discover":
            start_dir = str(
                args.get(
                    "start_dir",
                    "tests",
                )
            )

            start_path = (
                cwd / start_dir
            ).resolve()

            self.local._path(
                str(start_path)
            )

            if not start_path.is_dir():
                raise NotADirectoryError(
                    str(start_path)
                )

            pattern = str(
                args.get(
                    "pattern",
                    "test*.py",
                )
            )

            if (
                not pattern
                or "/" in pattern
                or "\\" in pattern
                or len(pattern) > 120
            ):
                raise ValueError(
                    "unittest pattern must be a basename pattern"
                )

            argv = [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(start_path),
                "-p",
                pattern,
            ]

        elif mode == "targets":
            targets = args.get(
                "targets"
            )

            if (
                not isinstance(
                    targets,
                    (list, tuple),
                )
                or not targets
            ):
                raise ValueError(
                    "targets mode requires a non-empty targets list"
                )

            if len(targets) > 20:
                raise ValueError(
                    "at most 20 unittest targets are allowed"
                )

            clean = []

            for target in targets:
                if (
                    not isinstance(target, str)
                    or not re.fullmatch(
                        r"[A-Za-z0-9_.]+",
                        target,
                    )
                ):
                    raise ValueError(
                        "invalid unittest target"
                    )

                clean.append(target)

            argv = [
                sys.executable,
                "-m",
                "unittest",
                *clean,
            ]

        else:
            raise ValueError(
                "unittest mode must be discover or targets"
            )

        return self._run(
            argv,
            cwd,
            timeout,
            max_chars=50000,
        )


def register_stage7_tools(
    registry: ToolRegistry,
    local_factory,
    repo_root: Path,
) -> None:
    """Register the expanded Stage 7B tool surface."""

    factory = Stage7ToolFactory(
        local_factory,
        repo_root,
    )

    registry.register(
        ToolSpec(
            "file.stat",
            ToolPermission.READ,
            "Inspect bounded filesystem metadata beneath an allowed root.",
            factory.file_stat,
        )
    )

    registry.register(
        ToolSpec(
            "file.glob",
            ToolPermission.READ,
            "Find files/directories by a bounded glob beneath an allowed root.",
            factory.file_glob,
        )
    )

    registry.register(
        ToolSpec(
            "file.hash",
            ToolPermission.READ,
            "Compute a bounded SHA-256 digest for an allowed local file.",
            factory.file_hash,
        )
    )

    registry.register(
        ToolSpec(
            "process.which",
            ToolPermission.READ,
            "Resolve whether a named executable exists on the local PATH.",
            factory.process_which,
        )
    )

    registry.register(
        ToolSpec(
            "git.status",
            ToolPermission.READ,
            "Read Git branch and working-tree status without modifying the repository.",
            factory.git_status,
        )
    )

    registry.register(
        ToolSpec(
            "git.diff",
            ToolPermission.READ,
            "Read the bounded unstaged or staged Git diff without modifying the repository.",
            factory.git_diff,
        )
    )

    registry.register(
        ToolSpec(
            "python.unittest",
            ToolPermission.EXECUTE,
            "Run bounded Python unittest discovery or explicit test targets inside an allowed root.",
            factory.python_unittest,
        )
    )
