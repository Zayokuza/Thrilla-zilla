"""Scoped persistent network authorization for Thrilla Stage 5."""

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import urlparse


class NetworkPermissionError(PermissionError):
    """Raised when a network operation is not authorized."""


class NetworkOperation(str, Enum):
    PUBLIC_READ = "public_read"
    AUTH_READ = "auth_read"
    WRITE = "write"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_site(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("site must not be empty")

    if "://" in text:
        parsed = urlparse(text)
    else:
        parsed = urlparse("//" + text)

    host = parsed.hostname
    if host is None:
        parsed = urlparse("https://" + text)
        host = parsed.hostname

    if not host:
        raise ValueError("site must contain a hostname")

    return host.rstrip(".").lower()


def _normalize_account(value: str) -> str:
    account = str(value).strip()
    if not account:
        raise ValueError("account must not be empty")
    return account


@dataclass(frozen=True)
class ReadAuthorization:
    site: str
    account: str
    scope: str
    authorized_at: str


class AuthorizationStore:
    """Persist read authorization metadata without storing credentials."""

    def __init__(self, state_root: Path) -> None:
        self.state_root = Path(state_root)
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.path = self.state_root / "network-authorizations.json"
        self._lock = threading.RLock()
        self._authorizations: Dict[Tuple[str, str], ReadAuthorization] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        entries = payload.get("read_authorizations", [])
        if not isinstance(entries, list):
            return

        for item in entries:
            if not isinstance(item, dict):
                continue
            try:
                site = _normalize_site(item["site"])
                account = _normalize_account(item["account"])
            except (KeyError, TypeError, ValueError):
                continue

            authorization = ReadAuthorization(
                site=site,
                account=account,
                scope="read",
                authorized_at=str(item.get("authorized_at", "")),
            )
            self._authorizations[(site, account)] = authorization

    def _persist(self) -> None:
        payload = {
            "read_authorizations": [
                {
                    "site": auth.site,
                    "account": auth.account,
                    "scope": auth.scope,
                    "authorized_at": auth.authorized_at,
                }
                for _, auth in sorted(self._authorizations.items())
            ]
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def authorize_read(
        self,
        site: str,
        account: str,
    ) -> ReadAuthorization:
        normalized_site = _normalize_site(site)
        normalized_account = _normalize_account(account)
        authorization = ReadAuthorization(
            site=normalized_site,
            account=normalized_account,
            scope="read",
            authorized_at=_utc_now(),
        )

        with self._lock:
            self._authorizations[
                (normalized_site, normalized_account)
            ] = authorization
            self._persist()

        return authorization

    def can_read(
        self,
        site: str,
        account: str,
    ) -> bool:
        normalized_site = _normalize_site(site)
        normalized_account = _normalize_account(account)
        with self._lock:
            return (
                normalized_site,
                normalized_account,
            ) in self._authorizations

    def revoke_read(
        self,
        site: str,
        account: str,
    ) -> bool:
        normalized_site = _normalize_site(site)
        normalized_account = _normalize_account(account)

        with self._lock:
            key = (normalized_site, normalized_account)
            if key not in self._authorizations:
                return False
            del self._authorizations[key]
            self._persist()
            return True


class NetworkPolicy:
    """Keep public read, authenticated read, and writes strictly separate."""

    def __init__(
        self,
        *,
        public_read_enabled: bool,
        write_enabled: bool,
        authorization_store: AuthorizationStore,
    ) -> None:
        self.public_read_enabled = bool(public_read_enabled)
        self.write_enabled = bool(write_enabled)
        self.authorization_store = authorization_store

    def require(
        self,
        operation: NetworkOperation,
        target: str,
        *,
        account: str = "",
    ) -> None:
        try:
            operation = NetworkOperation(operation)
        except ValueError as error:
            raise NetworkPermissionError(
                "unknown network operation"
            ) from error

        site = _normalize_site(target)

        if operation is NetworkOperation.PUBLIC_READ:
            if not self.public_read_enabled:
                raise NetworkPermissionError(
                    "public network reads are disabled"
                )
            return

        if operation is NetworkOperation.AUTH_READ:
            if not account:
                raise NetworkPermissionError(
                    "authenticated read requires an account scope"
                )
            if not self.authorization_store.can_read(site, account):
                raise NetworkPermissionError(
                    "authenticated read is not authorized for this site/account"
                )
            return

        if operation is NetworkOperation.WRITE:
            if not self.write_enabled:
                raise NetworkPermissionError(
                    "network writes are disabled"
                )
            return

        raise NetworkPermissionError(
            "network operation is not authorized"
        )

