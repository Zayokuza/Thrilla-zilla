"""Visible checks for the phone-first Thrilla runtime."""

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .config import Config
from .donors import DonorRegistry
from .model import LocalModelClient


@dataclass(frozen=True)
class Check:
    name: str
    level: str
    detail: str


def platform_name() -> str:
    if os.name == "nt":
        return "Windows"
    if sys.platform.startswith(("cygwin", "msys")):
        return "Windows / POSIX layer"
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix or "ANDROID_ROOT" in os.environ:
        return "Android / Termux"
    return platform.system() or "Unknown"


def run_checks(config: Config, include_model: bool = True) -> List[Check]:
    checks: List[Check] = []
    version_ok = sys.version_info >= (3, 9)
    checks.append(Check(
        "Python",
        "pass" if version_ok else "fail",
        f"{platform.python_version()} (3.9+ required)",
    ))

    target = platform_name()
    supported = target == "Android / Termux" or target.startswith("Windows")
    checks.append(Check(
        "Platform",
        "pass" if supported else "warn",
        target + ("" if supported else " (development host; release targets are Android and Windows)"),
    ))

    checks.append(Check(
        "Git",
        "pass" if shutil.which("git") else "fail",
        shutil.which("git") or "git was not found on PATH",
    ))

    registry = DonorRegistry(config.donor_path)
    ready, total = registry.progress(1)
    if ready == total == 100:
        donor_level = "pass"
    elif ready:
        donor_level = "warn"
    else:
        donor_level = "fail"
    checks.append(Check(
        "Phase-1 donors",
        donor_level,
        f"{ready}/{total} at {config.donor_path}",
    ))
    priority_ready, priority_total = registry.priority_progress()
    checks.append(Check(
        "Priority donors",
        "pass" if priority_ready == priority_total else "warn",
        f"{priority_ready}/{priority_total}",
    ))

    state_parent = config.state_path if config.state_path.exists() else config.state_path.parent
    writable = state_parent.exists() and os.access(str(state_parent), os.W_OK)
    checks.append(Check(
        "State storage",
        "pass" if writable else "fail",
        f"{config.state_path} ({'writable' if writable else 'not writable'})",
    ))

    if include_model:
        status = LocalModelClient(
            config.model_url,
            config.model_name,
            config.request_timeout,
        ).health()
        checks.append(Check(
            "Local model",
            "pass" if status.online else "warn",
            status.detail,
        ))
    return checks
