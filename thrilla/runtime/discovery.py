"""Local runtime discovery helpers."""

import os
import shutil
from pathlib import Path
from typing import Optional


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

