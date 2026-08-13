"""Compact interactive menu primitives for Termux and Windows terminals."""

import os
import re
import select
import shutil
import sys
from dataclasses import dataclass
from typing import IO, Optional, Sequence

from .colors import Palette


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: str
    description: str = ""


def terminal_width() -> int:
    return max(24, min(88, shutil.get_terminal_size((60, 24)).columns))


def clear_screen(stream: IO[str] = sys.stdout) -> None:
    if getattr(stream, "isatty", lambda: False)():
        stream.write("\033[2J\033[H")
        stream.flush()


def normalize_choice(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def parse_choice(value: str, items: Sequence[MenuItem]) -> Optional[str]:
    normalized = normalize_choice(value)
    if not normalized:
        return None
    first = normalized.split()[0]
    for item in items:
        if first == normalize_choice(item.key):
            return item.key
    for item in items:
        label = normalize_choice(item.label)
        if normalized == label or label.startswith(normalized):
            return item.key
    if first in {"q", "quit", "exit", "back"}:
        return "0"
    return None


def _read_windows_key(stream: IO[str]) -> str:
    import msvcrt

    key = msvcrt.getwch()
    if key in {"\x00", "\xe0"}:
        suffix = msvcrt.getwch()
        return {"H": "UP", "P": "DOWN"}.get(suffix, suffix)
    return "ENTER" if key == "\r" else key


def _read_posix_key(stream: IO[str]) -> str:
    import termios
    import tty

    file_descriptor = stream.fileno()
    previous = termios.tcgetattr(file_descriptor)
    try:
        # TCSANOW preserves already-typed keys. The default TCSAFLUSH can drop
        # Enter when a phone sends "5" and Enter in the same input packet.
        tty.setraw(file_descriptor, when=termios.TCSANOW)
        raw = os.read(file_descriptor, 1)
        if not raw:
            return "EOF"
        key = raw.decode("utf-8", "ignore")
        if key == "\x1b":
            sequence = key
            while select.select([file_descriptor], [], [], 0.025)[0]:
                sequence += os.read(file_descriptor, 1).decode("utf-8", "ignore")
            return {"\x1b[A": "UP", "\x1bOA": "UP", "\x1b[B": "DOWN", "\x1bOB": "DOWN"}.get(sequence, "ESC")
        if key in {"\r", "\n"}:
            return "ENTER"
        if key == "\x03":
            raise KeyboardInterrupt
        return key
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, previous)


def read_key(stream: IO[str] = sys.stdin) -> str:
    return _read_windows_key(stream) if os.name == "nt" else _read_posix_key(stream)


def _render_menu(
    title: str,
    items: Sequence[MenuItem],
    selected: int,
    palette: Palette,
    stream: IO[str],
    footer: str,
) -> None:
    clear_screen(stream)
    size = shutil.get_terminal_size((60, 24))
    width = max(24, min(88, size.columns))
    stream.write(palette.brand(title) + "\n")
    stream.write(palette.muted("─" * min(width, 62)) + "\n")
    # A phone keyboard can cut the usable terminal height in half. Descriptions
    # disappear automatically before they can push numbered actions off-screen.
    roomy = width >= 52 and size.lines >= len(items) * 2 + 6
    for index, item in enumerate(items):
        pointer = "▶" if index == selected else " "
        key = f"{item.key}."
        line = f"{pointer} {key:<3} {item.label}"
        if index == selected:
            line = palette.paint(line, "selected")
        elif item.key == "0":
            line = palette.muted(line)
        else:
            line = palette.accent(line)
        stream.write(line + "\n")
        if roomy and item.description:
            stream.write("      " + palette.muted(item.description) + "\n")
    stream.write("\n" + palette.muted(footer) + "\n")
    stream.flush()


def select_menu(
    title: str,
    items: Sequence[MenuItem],
    palette: Palette,
    stream: IO[str] = sys.stdout,
    input_stream: IO[str] = sys.stdin,
    footer: str = "↑/↓ move  •  Enter select  •  number + Enter  •  q back",
) -> str:
    if not items:
        raise ValueError("Menu requires at least one item.")
    interactive = bool(
        getattr(stream, "isatty", lambda: False)()
        and getattr(input_stream, "isatty", lambda: False)()
    )
    if not interactive:
        stream.write(title + "\n")
        for item in items:
            stream.write(f"{item.key}. {item.label}\n")
        while True:
            try:
                value = input("thrilla> ")
            except (EOFError, KeyboardInterrupt):
                stream.write("\n")
                return "0"
            choice = parse_choice(value, items)
            if choice is not None:
                return choice
            stream.write("Unknown choice. Enter a listed number or name.\n")

    selected = 0
    while True:
        _render_menu(title, items, selected, palette, stream, footer)
        try:
            key = read_key(input_stream)
        except KeyboardInterrupt:
            # Ctrl+C means "back" in a submenu and clean exit at the main
            # menu. _read_posix_key restores terminal settings in its finally
            # block before this exception reaches us.
            stream.write("\n")
            stream.flush()
            return "0"
        if key == "UP":
            selected = (selected - 1) % len(items)
        elif key == "DOWN":
            selected = (selected + 1) % len(items)
        elif key == "ENTER":
            return items[selected].key
        elif key in {"q", "Q", "ESC", "EOF"}:
            return "0"
        elif key.isdigit():
            for index, item in enumerate(items):
                if item.key == key:
                    selected = index
                    break
