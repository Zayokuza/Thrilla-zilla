"""Permanent Thrilla creator and installation-owner identity."""

from dataclasses import dataclass


CREATOR_NAME = "Jesse James"


@dataclass(frozen=True)
class ThrillaIdentity:
    creator: str
    owner: str


def identity_for(owner_name: str) -> ThrillaIdentity:
    return ThrillaIdentity(
        creator=CREATOR_NAME,
        owner=owner_name,
    )
