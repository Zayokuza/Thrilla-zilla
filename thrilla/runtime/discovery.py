"""Local runtime discovery helpers."""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ModelCandidate, ModelRole


def find_llama_server() -> Optional[str]:
    """Return a usable llama-server executable, or None."""
    found = shutil.which("llama-server")
    if found:
        return found

    prefix = os.environ.get("PREFIX")
    if not prefix:
        return None

    candidate = Path(prefix) / "bin" / "llama-server"

    if candidate.is_file() and os.access(str(candidate), os.X_OK):
        return str(candidate)

    return None


def discover_gguf_files(roots):
    """Return GGUF files found recursively beneath the supplied roots."""
    found = set()

    for root in roots:
        root_path = Path(root)

        for candidate in root_path.rglob("*.gguf"):
            if candidate.is_file():
                found.add(str(candidate.resolve()))

    return sorted(found)

def is_normal_chat_gguf(path):
    """Return whether a GGUF is suitable for normal chat inventory."""
    candidate = Path(path)
    name = candidate.name.lower()

    if name.startswith("ggml-vocab-"):
        return False

    parts = {part.lower() for part in candidate.parts}

    if "test" in parts or "tests" in parts:
        return False

    return True

def discover_chat_gguf_files(roots):
    """Return GGUF files suitable for normal chat inventory."""
    return [
        path
        for path in discover_gguf_files(roots)
        if is_normal_chat_gguf(path)
    ]


def infer_model_role(path):
    """Infer only clear specialist roles from a GGUF filename."""
    name = Path(path).name.lower()

    if "embed" in name:
        return ModelRole.EMBEDDING

    if "planner" in name:
        return ModelRole.PLANNER

    if "coder" in name or "coding" in name:
        return ModelRole.CODING

    return ModelRole.UNKNOWN


def infer_quantization(path):
    """Infer common GGUF quantization tokens from a filename."""
    stem = Path(path).stem

    match = re.search(
        r"(?i)(?<![A-Za-z0-9])((?:IQ|Q)\d+(?:_[A-Za-z0-9]+)*)",
        stem,
    )

    if not match:
        return "unknown"

    return match.group(1).upper()

def candidate_from_gguf(path, source="local"):
    """Build conservative metadata for one discovered GGUF model."""
    resolved = Path(path).expanduser().resolve()

    return ModelCandidate(
        path=str(resolved),
        filename=resolved.name,
        size_bytes=resolved.stat().st_size,
        architecture="unknown",
        quantization=infer_quantization(resolved),
        role=infer_model_role(resolved),
        context_capability=0,
        readable=resolved.is_file()
        and os.access(str(resolved), os.R_OK),
        compatibility="unknown",
        source=source,
        last_verified=datetime.now().astimezone().isoformat(),
        score=0.0,
    )

def build_model_inventory(roots, source="local"):
    """Build structured candidate records for discovered model GGUFs."""
    inventory = []

    for path in discover_gguf_files(roots):
        if not is_normal_chat_gguf(path):
            continue

        inventory.append(
            candidate_from_gguf(
                path,
                source=source,
            )
        )

    return inventory

