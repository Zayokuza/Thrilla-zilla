"""Structured local tool contracts and bounded Stage-2 executor."""

import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple


class ToolPermission(str, Enum):
    READ = "READ"
    EXECUTE = "EXECUTE"
    WRITE = "WRITE"
    NETWORK = "NETWORK"
    DEVICE = "DEVICE"


@dataclass(frozen=True)
class ToolEvidence:
    source: str
    detail: str


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    permission: ToolPermission
    output: Any
    evidence: Tuple[ToolEvidence, ...]
    error: str
    duration_ms: int


@dataclass(frozen=True)
class ToolSpec:
    name: str
    permission: ToolPermission
    description: str
    handler: Callable[[Mapping[str, Any]], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name:
            raise ValueError("tool name must not be empty")
        if spec.name in self._specs:
            raise ValueError("tool already registered: {0}".format(spec.name))
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as error:
            raise KeyError("unknown tool: {0}".format(name)) from error

    @property
    def names(self) -> Tuple[str, ...]:
        return tuple(sorted(self._specs))

    @property
    def catalog(self) -> Tuple[Dict[str, str], ...]:
        """Return deterministic model-safe tool metadata."""
        return tuple(
            {
                "name": spec.name,
                "permission": spec.permission.value,
                "description": spec.description,
            }
            for spec in (
                self._specs[name]
                for name in sorted(self._specs)
            )
        )


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        name: str,
        arguments: Optional[Mapping[str, Any]] = None,
    ) -> ToolResult:
        started = time.monotonic()
        payload = dict(arguments or {})
        try:
            spec = self.registry.get(name)
        except KeyError as error:
            return ToolResult(
                tool=name,
                ok=False,
                permission=ToolPermission.READ,
                output=None,
                evidence=(),
                error=str(error),
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        try:
            output = spec.handler(payload)
            evidence = _evidence_from_output(name, output)
            return ToolResult(
                tool=name,
                ok=True,
                permission=spec.permission,
                output=output,
                evidence=evidence,
                error="",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as error:
            return ToolResult(
                tool=name,
                ok=False,
                permission=spec.permission,
                output=None,
                evidence=(),
                error="{0}: {1}".format(type(error).__name__, error),
                duration_ms=int((time.monotonic() - started) * 1000),
            )


def _evidence_from_output(tool: str, output: Any) -> Tuple[ToolEvidence, ...]:
    if isinstance(output, dict):
        source = output.get("source")
        detail = output.get("detail")
        if isinstance(source, str) and isinstance(detail, str):
            return (ToolEvidence(source=source, detail=detail),)
    return (
        ToolEvidence(
            source="tool:{0}".format(tool),
            detail="structured tool result",
        ),
    )


class LocalToolFactory:
    READ_ONLY_COMMANDS = {"pwd", "uname"}
    READ_ONLY_GIT_SUBCOMMANDS = {"status", "diff", "log", "show", "rev-parse"}

    def __init__(self, allowed_roots: Iterable[Path]) -> None:
        roots = []
        for root in allowed_roots:
            resolved = Path(root).expanduser().resolve()
            if resolved not in roots:
                roots.append(resolved)
        if not roots:
            raise ValueError("at least one allowed root is required")
        self.allowed_roots = tuple(roots)

    def _path(self, value: Any) -> Path:
        if not isinstance(value, str) or not value:
            raise ValueError("path must be a non-empty string")
        candidate = Path(value).expanduser().resolve()
        if not any(
            candidate == root or root in candidate.parents
            for root in self.allowed_roots
        ):
            raise PermissionError(
                "path is outside Thrilla allowed roots: {0}".format(candidate)
            )
        return candidate

    def read_text(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        path = self._path(args.get("path"))
        max_chars = max(1, min(int(args.get("max_chars", 20000)), 200000))
        text = path.read_text(encoding="utf-8", errors="replace")
        return {
            "source": str(path),
            "detail": "read {0} characters".format(min(len(text), max_chars)),
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
        }

    def list_dir(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        path = self._path(args.get("path"))
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        entries = [
            {
                "name": child.name,
                "type": "directory" if child.is_dir() else "file",
            }
            for child in sorted(path.iterdir(), key=lambda item: item.name.lower())
        ]
        return {
            "source": str(path),
            "detail": "listed {0} entries".format(len(entries)),
            "entries": entries,
        }

    def search_text(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        root = self._path(args.get("path"))
        query = args.get("query")
        if not isinstance(query, str) or not query:
            raise ValueError("query must be a non-empty string")
        max_matches = max(1, min(int(args.get("max_matches", 50)), 500))
        files = (root,) if root.is_file() else (
            path for path in root.rglob("*") if path.is_file()
        )
        matches = []
        for path in files:
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                lines = path.read_text(
                    encoding="utf-8", errors="strict"
                ).splitlines()
            except (OSError, UnicodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if query.lower() in line.lower():
                    matches.append(
                        {
                            "path": str(path),
                            "line": number,
                            "text": line[:500],
                        }
                    )
                    if len(matches) >= max_matches:
                        break
            if len(matches) >= max_matches:
                break
        return {
            "source": str(root),
            "detail": "found {0} text matches".format(len(matches)),
            "query": query,
            "matches": matches,
            "truncated": len(matches) >= max_matches,
        }

    def system_info(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        del args
        memory_total = None
        memory_available = None
        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            try:
                values = {}
                for line in meminfo.read_text(encoding="utf-8").splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        values[key] = int(value.strip().split()[0])
                memory_total = values.get("MemTotal")
                memory_available = values.get("MemAvailable")
            except (OSError, ValueError, IndexError):
                pass
        disk = shutil.disk_usage(str(self.allowed_roots[0]))
        return {
            "source": "local-system",
            "detail": "observed local platform and resource metadata",
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_total_kib": memory_total,
            "memory_available_kib": memory_available,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "disk_free": disk.free,
        }

    def run_process(self, args: Mapping[str, Any]) -> Dict[str, Any]:
        argv = args.get("argv")
        if (
            not isinstance(argv, (list, tuple))
            or not argv
            or not all(isinstance(part, str) and part for part in argv)
        ):
            raise ValueError("argv must be a non-empty list of strings")
        if len(argv) > 32:
            raise ValueError("argv may contain at most 32 arguments")

        command = Path(argv[0]).name
        if command == "git":
            if len(argv) < 2 or argv[1] not in self.READ_ONLY_GIT_SUBCOMMANDS:
                raise PermissionError(
                    "git subcommand is not enabled in Stage 2"
                )
        elif command not in self.READ_ONLY_COMMANDS:
            raise PermissionError(
                "process command is not enabled in Stage 2: {0}".format(command)
            )

        cwd = self._path(args.get("cwd", str(self.allowed_roots[0])))
        if not cwd.is_dir():
            raise NotADirectoryError(str(cwd))

        timeout = max(0.1, min(float(args.get("timeout", 10.0)), 30.0))
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
            "source": "process:{0}".format(command),
            "detail": "process exited with code {0}".format(completed.returncode),
            "argv": list(argv),
            "cwd": str(cwd),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20000:],
            "stderr": completed.stderr[-20000:],
        }


def build_default_tool_executor(
    repo_root: Path,
    state_root: Path,
    donor_root: Path,
) -> ToolExecutor:
    factory = LocalToolFactory((repo_root, state_root, donor_root))
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "file.read_text",
            ToolPermission.READ,
            "Read UTF-8-compatible text beneath an allowed root.",
            factory.read_text,
        )
    )
    registry.register(
        ToolSpec(
            "file.list",
            ToolPermission.READ,
            "List one directory beneath an allowed root.",
            factory.list_dir,
        )
    )
    registry.register(
        ToolSpec(
            "file.search_text",
            ToolPermission.READ,
            "Search text recursively beneath an allowed root.",
            factory.search_text,
        )
    )
    registry.register(
        ToolSpec(
            "system.info",
            ToolPermission.DEVICE,
            "Observe local OS, CPU, memory and storage metadata.",
            factory.system_info,
        )
    )
    registry.register(
        ToolSpec(
            "process.run",
            ToolPermission.EXECUTE,
            "Run a bounded read-only inspection command without a shell.",
            factory.run_process,
        )
    )

    # Imported lazily to avoid a module-import cycle while keeping
    # Stage-7 tool implementations isolated from the core contracts.
    from .toolkit import register_stage7_tools

    register_stage7_tools(
        registry,
        factory,
        repo_root,
    )

    return ToolExecutor(registry)
