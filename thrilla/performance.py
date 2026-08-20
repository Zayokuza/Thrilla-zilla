"""Low-overhead reusable indexes and caches for Thrilla Stage 7."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple


@dataclass(frozen=True)
class IndexedFile:
    """One cached repository source observation."""

    relative: str
    size: int
    mtime_ns: int
    content: str


class RepositoryIndex:
    """Cache source text until the corresponding file changes."""

    def __init__(
        self,
        repo_root: Path,
        search_roots: Sequence[str],
        supported_suffixes: Iterable[str],
        *,
        max_file_bytes: int = 250_000,
        content_chars: int = 30_000,
        reader: Optional[Callable[[Path], str]] = None,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.search_roots = tuple(str(item) for item in search_roots)
        self.supported_suffixes = frozenset(
            str(item).lower()
            for item in supported_suffixes
        )
        self.max_file_bytes = max(
            1,
            int(max_file_bytes),
        )
        self.content_chars = max(
            1,
            int(content_chars),
        )
        self._reader = (
            reader
            if reader is not None
            else self._read_text
        )
        self._cache: Dict[str, IndexedFile] = {}

    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    def clear(self) -> None:
        self._cache.clear()

    @property
    def cached_files(self) -> int:
        return len(self._cache)

    def _files(self):
        for root_name in self.search_roots:
            root = self.repo_root / root_name

            if not root.exists():
                continue

            if root.is_file():
                files = (root,)
            else:
                files = (
                    path
                    for path in root.rglob("*")
                    if path.is_file()
                )

            for path in files:
                if (
                    path.suffix.lower()
                    not in self.supported_suffixes
                ):
                    continue

                yield path

    def _entry(
        self,
        path: Path,
    ) -> Optional[IndexedFile]:
        try:
            stat = path.stat()
        except OSError:
            return None

        if stat.st_size > self.max_file_bytes:
            return None

        try:
            relative = str(
                path.relative_to(self.repo_root)
            )
        except ValueError:
            return None

        cached = self._cache.get(relative)

        if (
            cached is not None
            and cached.size == stat.st_size
            and cached.mtime_ns == stat.st_mtime_ns
        ):
            return cached

        try:
            content = self._reader(path)
        except (OSError, UnicodeError):
            return None

        entry = IndexedFile(
            relative=relative,
            size=int(stat.st_size),
            mtime_ns=int(stat.st_mtime_ns),
            content=content[
                : self.content_chars
            ].lower(),
        )

        self._cache[relative] = entry
        return entry

    def rank(
        self,
        tokens: Sequence[str],
        max_files: int = 3,
    ) -> Tuple[str, ...]:
        limit = max(
            1,
            min(int(max_files), 10),
        )

        normalized_tokens = tuple(
            str(token).lower()
            for token in tokens
            if str(token)
        )

        ranked = []
        seen = set()

        for path in self._files():
            entry = self._entry(path)

            if entry is None:
                continue

            seen.add(entry.relative)

            haystack = (
                entry.relative.lower()
                + "\n"
                + entry.content
            )

            score = sum(
                haystack.count(token)
                for token in normalized_tokens
            )

            # Preserve the existing useful bias toward Thrilla's
            # application integration surface.
            if entry.relative == "thrilla/app.py":
                score += 1

            if score > 0:
                ranked.append(
                    (
                        score,
                        -len(entry.relative),
                        entry.relative,
                    )
                )

        # Forget files that disappeared from the indexed roots.
        for relative in tuple(self._cache):
            if relative not in seen:
                self._cache.pop(relative, None)

        ranked.sort(reverse=True)

        return tuple(
            item[2]
            for item in ranked[:limit]
        )
