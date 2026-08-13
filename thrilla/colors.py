"""Dependency-free ANSI color support with accessibility fallbacks."""

import os
import re
import sys
from enum import Enum
from typing import IO, Optional


class ColorMode(str, Enum):
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "brand": "\033[1;95m",
    "accent": "\033[1;96m",
    "prompt": "\033[1;96m",
    "answer": "\033[1;92m",
    "success": "\033[1;92m",
    "warning": "\033[1;93m",
    "error": "\033[1;91m",
    "muted": "\033[90m",
    "selected": "\033[30;106m",
}

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _enable_windows_ansi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


class Palette:
    """Applies semantic terminal colors only when the terminal supports them."""

    def __init__(
        self,
        mode: ColorMode = ColorMode.AUTO,
        stream: Optional[IO[str]] = None,
    ) -> None:
        self.mode = ColorMode(mode)
        self.stream = stream or sys.stdout
        _enable_windows_ansi()
        no_color = "NO_COLOR" in os.environ
        if self.mode is ColorMode.ALWAYS:
            self.enabled = True
        elif self.mode is ColorMode.NEVER or no_color:
            self.enabled = False
        else:
            self.enabled = bool(getattr(self.stream, "isatty", lambda: False)())

    def paint(self, text: object, style: str) -> str:
        value = str(text)
        if not self.enabled:
            return value
        prefix = ANSI.get(style, "")
        return f"{prefix}{value}{ANSI['reset']}" if prefix else value

    def start(self, style: str) -> str:
        """Begin a style without resetting, useful while a user is typing."""
        return ANSI.get(style, "") if self.enabled else ""

    @property
    def reset_code(self) -> str:
        return ANSI["reset"] if self.enabled else ""

    def brand(self, text: object) -> str:
        return self.paint(text, "brand")

    def accent(self, text: object) -> str:
        return self.paint(text, "accent")

    def success(self, text: object) -> str:
        return self.paint(text, "success")

    def prompt(self, text: object) -> str:
        return self.paint(text, "prompt")

    def answer(self, text: object) -> str:
        return self.paint(text, "answer")

    def warning(self, text: object) -> str:
        return self.paint(text, "warning")

    def error(self, text: object) -> str:
        return self.paint(text, "error")

    def muted(self, text: object) -> str:
        return self.paint(text, "muted")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)
