"""Fast durable hybrid memory for Thrilla-zilla."""

import hashlib
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple


class MemoryError(RuntimeError):
    """Base durable-memory failure."""


class MemoryRejected(MemoryError):
    """A candidate was rejected instead of being persisted."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _tokens(value: str) -> Tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(value))
        if len(token) > 1
    )


_SENSITIVE_TERMS = (
    "password",
    "passcode",
    "api key",
    "api_key",
    "secret key",
    "private key",
    "seed phrase",
    "recovery phrase",
    "mnemonic",
    "access token",
    "auth token",
    "bearer token",
    "social security",
    "ssn",
    "credit card",
    "cvv",
)

_SENSITIVE_PATTERNS = (
    re.compile(r"\bsk-[a-z0-9_-]{12,}\b", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[a-z0-9]{20,}\b", re.IGNORECASE),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
)


def looks_sensitive(value: str) -> bool:
    normalized = _normalize(value)

    if any(term in normalized for term in _SENSITIVE_TERMS):
        return True

    return any(pattern.search(value) for pattern in _SENSITIVE_PATTERNS)


@dataclass(frozen=True)
class MemoryFact:
    fact_id: int
    category: str
    subject: str
    predicate: str
    value: str
    confidence: float
    source: str
    source_timestamp: str
    created_at: str
    updated_at: str
    status: str
    supersedes_id: Optional[int]
    raw_source: str


@dataclass(frozen=True)
class MemoryCandidate:
    category: str
    subject: str
    predicate: str
    value: str
    confidence: float


class MemoryStore:
    """SQLite persistence with an in-process active-fact cache."""

    def __init__(self, state_root: Path) -> None:
        self.state_root = Path(state_root).expanduser()
        self.path = self.state_root / "memory.sqlite3"
        self._connection: Optional[sqlite3.Connection] = None
        self._active_cache: Optional[Tuple[MemoryFact, ...]] = None
        self._key_cache = {}
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            self._active_cache = None
            self._key_cache = {}

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _connect(self) -> sqlite3.Connection:
        with self._lock:
            if self._connection is not None:
                return self._connection

            self.path.parent.mkdir(parents=True, exist_ok=True)

            connection = sqlite3.connect(
                str(self.path),
                timeout=5.0,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    source_timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    supersedes_id INTEGER,
                    raw_source TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_facts_active_key
                    ON facts(status, subject, predicate);

                CREATE INDEX IF NOT EXISTS idx_facts_active_category
                    ON facts(status, category);

                CREATE INDEX IF NOT EXISTS idx_facts_updated
                    ON facts(status, updated_at DESC);
                """
            )
            connection.commit()
            self._connection = connection
            return connection

    @staticmethod
    def _fact(row: sqlite3.Row) -> MemoryFact:
        return MemoryFact(
            fact_id=int(row["id"]),
            category=str(row["category"]),
            subject=str(row["subject"]),
            predicate=str(row["predicate"]),
            value=str(row["value"]),
            confidence=float(row["confidence"]),
            source=str(row["source"]),
            source_timestamp=str(row["source_timestamp"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            status=str(row["status"]),
            supersedes_id=(
                int(row["supersedes_id"])
                if row["supersedes_id"] is not None
                else None
            ),
            raw_source=str(row["raw_source"]),
        )

    def _invalidate(self) -> None:
        self._active_cache = None
        self._key_cache = {}

    def _active(self) -> Tuple[MemoryFact, ...]:
        with self._lock:
            if self._active_cache is not None:
                return self._active_cache

            rows = self._connect().execute(
                """
                SELECT
                    id,
                    category,
                    subject,
                    predicate,
                    value,
                    confidence,
                    source,
                    source_timestamp,
                    created_at,
                    updated_at,
                    status,
                    supersedes_id,
                    raw_source
                FROM facts
                WHERE status = 'active'
                ORDER BY id DESC
                """
            ).fetchall()

            facts = tuple(self._fact(row) for row in rows)
            self._active_cache = facts
            self._key_cache = {
                (
                    _normalize(fact.subject),
                    _normalize(fact.predicate),
                ): fact
                for fact in facts
            }
            return facts

    @property
    def connection_identity(self) -> int:
        return id(self._connect())

    def active(self, limit: Optional[int] = None) -> Tuple[MemoryFact, ...]:
        facts = self._active()

        if limit is None:
            return facts

        return facts[: max(0, int(limit))]

    def count(self) -> int:
        return len(self._active())

    def fact_for(
        self,
        subject: str,
        predicate: str,
    ) -> Optional[MemoryFact]:
        self._active()
        return self._key_cache.get(
            (
                _normalize(subject),
                _normalize(predicate),
            )
        )

    def remember(
        self,
        *,
        category: str,
        subject: str,
        predicate: str,
        value: str,
        confidence: float,
        source: str,
        raw_source: str = "",
        source_timestamp: Optional[str] = None,
    ) -> MemoryFact:
        fields = (
            category,
            subject,
            predicate,
            value,
            source,
            raw_source,
        )

        if any(looks_sensitive(field) for field in fields if field):
            raise MemoryRejected(
                "credential or secret-like content is not stored in durable memory"
            )

        category = _normalize(category) or "owner"
        subject = _normalize(subject) or "owner"
        predicate = _normalize(predicate).replace(" ", "_")
        value = " ".join(str(value).strip().split())
        source = _normalize(source) or "explicit"

        if not predicate or not value:
            raise MemoryRejected(
                "memory requires a non-empty predicate and value"
            )

        confidence = min(1.0, max(0.0, float(confidence)))
        timestamp = source_timestamp or _utc_now()
        now = _utc_now()

        with self._lock:
            connection = self._connect()
            current = self.fact_for(subject, predicate)

            if current is not None and _normalize(current.value) == _normalize(value):
                connection.execute(
                    """
                    UPDATE facts
                    SET
                        confidence = ?,
                        source = ?,
                        source_timestamp = ?,
                        updated_at = ?,
                        raw_source = ?
                    WHERE id = ?
                    """,
                    (
                        max(current.confidence, confidence),
                        (
                            "explicit"
                            if source == "explicit"
                            else current.source
                        ),
                        timestamp,
                        now,
                        raw_source,
                        current.fact_id,
                    ),
                )
                connection.commit()
                self._invalidate()
                refreshed = self.fact_for(subject, predicate)
                if refreshed is None:
                    raise MemoryError("updated fact vanished from active memory")
                return refreshed

            supersedes_id = None

            if current is not None:
                supersedes_id = current.fact_id
                connection.execute(
                    """
                    UPDATE facts
                    SET status = 'superseded', updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        now,
                        current.fact_id,
                    ),
                )

            cursor = connection.execute(
                """
                INSERT INTO facts (
                    category,
                    subject,
                    predicate,
                    value,
                    confidence,
                    source,
                    source_timestamp,
                    created_at,
                    updated_at,
                    status,
                    supersedes_id,
                    raw_source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    category,
                    subject,
                    predicate,
                    value,
                    confidence,
                    source,
                    timestamp,
                    now,
                    now,
                    supersedes_id,
                    raw_source,
                ),
            )
            connection.commit()
            fact_id = int(cursor.lastrowid)
            self._invalidate()

            row = connection.execute(
                """
                SELECT
                    id,
                    category,
                    subject,
                    predicate,
                    value,
                    confidence,
                    source,
                    source_timestamp,
                    created_at,
                    updated_at,
                    status,
                    supersedes_id,
                    raw_source
                FROM facts
                WHERE id = ?
                """,
                (fact_id,),
            ).fetchone()

            if row is None:
                raise MemoryError("inserted fact could not be read back")

            return self._fact(row)

    def search(
        self,
        query: str,
        limit: int = 8,
    ) -> Tuple[MemoryFact, ...]:
        normalized_query = _normalize(query)
        query_tokens = set(_tokens(query))

        if not normalized_query:
            return self.active(limit=limit)

        ranked = []

        for fact in self._active():
            subject = _normalize(fact.subject)
            predicate = _normalize(fact.predicate.replace("_", " "))
            value = _normalize(fact.value)
            combined = " ".join((subject, predicate, value))
            combined_tokens = set(_tokens(combined))

            overlap = len(query_tokens & combined_tokens)
            score = overlap * 5

            if normalized_query == value:
                score += 40
            if predicate and predicate in normalized_query:
                score += 25
            if subject and subject in normalized_query:
                score += 10
            if normalized_query in combined:
                score += 15

            if score:
                ranked.append(
                    (
                        score,
                        fact.confidence,
                        fact.fact_id,
                        fact,
                    )
                )

        ranked.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
            ),
            reverse=True,
        )

        return tuple(
            item[3]
            for item in ranked[: max(1, int(limit))]
        )

    def forget(self, query: str) -> int:
        matches = self.search(query, limit=12)

        if not matches:
            return 0

        ids = tuple(fact.fact_id for fact in matches)
        placeholders = ",".join("?" for _ in ids)
        now = _utc_now()

        with self._lock:
            connection = self._connect()
            cursor = connection.execute(
                """
                UPDATE facts
                SET status = 'deleted', updated_at = ?
                WHERE id IN ({0})
                AND status = 'active'
                """.format(placeholders),
                (now, *ids),
            )
            connection.commit()
            self._invalidate()
            return int(cursor.rowcount)


class HybridMemory:
    """Hybrid explicit + deterministic high-confidence automatic memory."""

    _NAME = re.compile(
        r"\b(?:my name is|call me|i am called)\s+(?P<value>[^.!?\n]{1,80}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )
    _PREFERRED = re.compile(
        r"\bmy preferred\s+(?P<key>[a-z0-9 _-]{2,40}?)\s+is\s+(?P<value>[^.!?\n]{1,160}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )
    _FAVORITE = re.compile(
        r"\bmy favorite\s+(?P<key>[a-z0-9 _-]{2,40}?)\s+(?:is|are)\s+(?P<value>[^.!?\n]{1,160}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )
    _DEVICE = re.compile(
        r"\bmy\s+(?P<key>phone|tablet|laptop|computer|operating system|os|local model)\s+is\s+(?P<value>[^.!?\n]{1,180}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )
    _LOCATION = re.compile(
        r"\bi live in\s+(?P<value>[^.!?\n]{1,120}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )
    _PROJECT_GOAL = re.compile(
        r"\bi want\s+(?P<project>thrilla(?:-zilla)?)\s+to\s+(?P<value>[^.!?\n]{3,240}?)(?=\s+and\s+(?:my|i)\b|[.!?\n]|$)",
        re.IGNORECASE,
    )

    def __init__(self, state_root: Path) -> None:
        self.store = MemoryStore(state_root)

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.strip(" \t\r\n.,!?").split())

    @staticmethod
    def _predicate(prefix: str, key: str) -> str:
        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            _normalize(key),
        ).strip("_")
        return "{0}_{1}".format(prefix, normalized)

    def extract_automatic(
        self,
        text: str,
    ) -> Tuple[MemoryCandidate, ...]:
        if looks_sensitive(text):
            return ()

        candidates = []

        name = self._NAME.search(text)
        if name:
            candidates.append(
                MemoryCandidate(
                    category="identity",
                    subject="owner",
                    predicate="name",
                    value=self._clean(name.group("value")),
                    confidence=0.99,
                )
            )

        preferred = self._PREFERRED.search(text)
        if preferred:
            candidates.append(
                MemoryCandidate(
                    category="preference",
                    subject="owner",
                    predicate=self._predicate(
                        "preferred",
                        preferred.group("key"),
                    ),
                    value=self._clean(preferred.group("value")),
                    confidence=0.96,
                )
            )

        favorite = self._FAVORITE.search(text)
        if favorite:
            candidates.append(
                MemoryCandidate(
                    category="preference",
                    subject="owner",
                    predicate=self._predicate(
                        "favorite",
                        favorite.group("key"),
                    ),
                    value=self._clean(favorite.group("value")),
                    confidence=0.96,
                )
            )

        device = self._DEVICE.search(text)
        if device:
            candidates.append(
                MemoryCandidate(
                    category="device",
                    subject="owner",
                    predicate=self._predicate(
                        "device",
                        device.group("key"),
                    ),
                    value=self._clean(device.group("value")),
                    confidence=0.94,
                )
            )

        location = self._LOCATION.search(text)
        if location:
            candidates.append(
                MemoryCandidate(
                    category="identity",
                    subject="owner",
                    predicate="location",
                    value=self._clean(location.group("value")),
                    confidence=0.94,
                )
            )

        goal = self._PROJECT_GOAL.search(text)
        if goal:
            project = _normalize(goal.group("project")).replace("-", "_")
            candidates.append(
                MemoryCandidate(
                    category="project",
                    subject=project,
                    predicate="owner_goal",
                    value=self._clean(goal.group("value")),
                    confidence=0.93,
                )
            )

        deduped = []
        seen = set()

        for candidate in candidates:
            key = (
                candidate.category,
                candidate.subject,
                candidate.predicate,
                _normalize(candidate.value),
            )
            if key not in seen and candidate.value:
                seen.add(key)
                deduped.append(candidate)

        return tuple(deduped)

    def _explicit_candidate(
        self,
        text: str,
    ) -> MemoryCandidate:
        automatic = self.extract_automatic(text)

        if automatic:
            candidate = automatic[0]
            return MemoryCandidate(
                category=candidate.category,
                subject=candidate.subject,
                predicate=candidate.predicate,
                value=candidate.value,
                confidence=1.0,
            )

        if looks_sensitive(text):
            raise MemoryRejected(
                "credential or secret-like content is not stored in durable memory"
            )

        cleaned = self._clean(text)

        if not cleaned:
            raise MemoryRejected("explicit memory is empty")

        digest = hashlib.blake2s(
            _normalize(cleaned).encode("utf-8"),
            digest_size=6,
        ).hexdigest()

        return MemoryCandidate(
            category="owner",
            subject="owner",
            predicate="note_{0}".format(digest),
            value=cleaned,
            confidence=1.0,
        )

    def _remember_candidate(
        self,
        candidate: MemoryCandidate,
        source: str,
        raw_source: str,
    ) -> MemoryFact:
        return self.store.remember(
            category=candidate.category,
            subject=candidate.subject,
            predicate=candidate.predicate,
            value=candidate.value,
            confidence=candidate.confidence,
            source=source,
            raw_source=raw_source,
        )

    def observe(
        self,
        owner_text: str,
    ) -> Tuple[MemoryFact, ...]:
        facts = []

        for candidate in self.extract_automatic(owner_text):
            try:
                facts.append(
                    self._remember_candidate(
                        candidate,
                        source="automatic",
                        raw_source=owner_text,
                    )
                )
            except MemoryRejected:
                continue

        return tuple(facts)

    def remember_explicit(
        self,
        owner_text: str,
    ) -> MemoryFact:
        candidate = self._explicit_candidate(owner_text)
        return self._remember_candidate(
            candidate,
            source="explicit",
            raw_source=owner_text,
        )

    def forget(self, query: str) -> int:
        return self.store.forget(query)

    def correct(
        self,
        query: str,
        replacement: str,
    ) -> MemoryFact:
        matches = self.store.search(query, limit=1)

        if not matches:
            raise MemoryError(
                "no active memory matched the correction query"
            )

        current = matches[0]
        automatic = self.extract_automatic(replacement)

        if automatic:
            candidate = automatic[0]
        else:
            cleaned = self._clean(replacement)

            if not cleaned:
                raise MemoryRejected("replacement memory is empty")

            candidate = MemoryCandidate(
                category=current.category,
                subject=current.subject,
                predicate=current.predicate,
                value=cleaned,
                confidence=1.0,
            )

        return self._remember_candidate(
            MemoryCandidate(
                category=candidate.category,
                subject=candidate.subject,
                predicate=candidate.predicate,
                value=candidate.value,
                confidence=1.0,
            ),
            source="explicit",
            raw_source=replacement,
        )

    def owner_name(
        self,
        configured_owner_name: str = "",
    ) -> str:
        fact = self.store.fact_for(
            "owner",
            "name",
        )

        if fact is not None:
            return fact.value

        return configured_owner_name.strip()

    @staticmethod
    def _owner_query(prompt: str) -> bool:
        normalized = _normalize(prompt)
        return (
            normalized in {
                "who am i",
                "what is my name",
                "what's my name",
                "what do you know about me",
                "what do you remember about me",
                "what do you know about the owner",
            }
            or normalized.startswith("what is my ")
            or normalized.startswith("what's my ")
            or normalized.startswith("what are my ")
        )

    def can_answer_owner_query(self, prompt: str) -> bool:
        return self._owner_query(prompt)

    def answer_owner_query(
        self,
        prompt: str,
        configured_owner_name: str = "",
    ) -> Optional[str]:
        normalized = _normalize(prompt)

        if normalized in {
            "who am i",
            "what is my name",
            "what's my name",
        }:
            name = self.owner_name(
                configured_owner_name
            )

            if not name:
                return None

            return "Your name is {0}.".format(name)

        if normalized in {
            "what do you know about me",
            "what do you remember about me",
            "what do you know about the owner",
        }:
            facts = tuple(
                fact
                for fact in self.store.active(limit=20)
                if fact.subject == "owner"
            )

            if configured_owner_name.strip() and not any(
                fact.predicate == "name"
                for fact in facts
            ):
                name_line = "name: {0}".format(
                    configured_owner_name.strip()
                )
            else:
                name_line = ""

            lines = []

            if name_line:
                lines.append(name_line)

            for fact in facts:
                label = fact.predicate.replace("_", " ")
                lines.append(
                    "{0}: {1} [{2}, {3:.0%}]".format(
                        label,
                        fact.value,
                        fact.source,
                        fact.confidence,
                    )
                )

            if not lines:
                return None

            return (
                "Durable owner memory:\n"
                + "\n".join(
                    "- " + line
                    for line in lines
                )
            )

        match = re.match(
            r"^(?:what is|what's|what are) my\s+(.+?)[?]?$",
            normalized,
        )

        if not match:
            return None

        topic = match.group(1).strip()
        matches = self.store.search(
            "owner " + topic,
            limit=1,
        )

        if not matches:
            return None

        fact = matches[0]
        label = fact.predicate.replace("_", " ")

        return "Your {0} is {1}.".format(
            label,
            fact.value,
        )

    def list_text(
        self,
        query: str = "",
        limit: int = 20,
    ) -> str:
        facts = (
            self.store.search(query, limit=limit)
            if query.strip()
            else self.store.active(limit=limit)
        )

        if not facts:
            return "No matching durable memories."

        lines = []

        for fact in facts:
            lines.append(
                "#{0} {1}/{2}/{3} = {4} "
                "[{5}, confidence={6:.0%}, status={7}]".format(
                    fact.fact_id,
                    fact.category,
                    fact.subject,
                    fact.predicate,
                    fact.value,
                    fact.source,
                    fact.confidence,
                    fact.status,
                )
            )

        return "\n".join(lines)
