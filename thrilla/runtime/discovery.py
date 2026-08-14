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
