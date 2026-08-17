"""Authority classification for owner requests and retrieved evidence."""

from dataclasses import dataclass
from typing import Optional

from .identity import ThrillaIdentity, identity_for


OWNER_AUTHORITY = "owner"
EVIDENCE_AUTHORITY = "evidence"
LOCAL_UI_SOURCE = "local-ui"


@dataclass(frozen=True)
class RequestContext:
    content: str
    source: str
    authority: str
    identity: Optional[ThrillaIdentity] = None

    @property
    def is_owner_authority(self) -> bool:
        return self.authority == OWNER_AUTHORITY


def owner_input(
    content: str,
    owner_name: str,
) -> RequestContext:
    """Classify direct trusted local UI input as owner input."""

    return RequestContext(
        content=content,
        source=LOCAL_UI_SOURCE,
        authority=OWNER_AUTHORITY,
        identity=identity_for(owner_name),
    )


def retrieved_content(
    content: str,
    source: str,
) -> RequestContext:
    """Classify retrieved material as evidence, never owner authority."""

    source_name = str(source).strip()

    if not source_name:
        raise ValueError("retrieved content requires a source")

    return RequestContext(
        content=content,
        source=source_name,
        authority=EVIDENCE_AUTHORITY,
        identity=None,
    )
