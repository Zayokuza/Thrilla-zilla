"""Creator Vault equipment identity and state normalization."""

from typing import Dict


EQUIPMENT_NAMES = (
    "sword",
    "shield",
    "helmet",
    "armor",
    "boots",
)

_CREATOR_CODE = "1989"


def verify_creator_code(value: str) -> bool:
    """Return whether the supplied Creator Vault code is exact."""

    return value == _CREATOR_CODE


def normalized_equipment_state(raw) -> Dict[str, bool]:
    """Return exactly the five known persistent equipment toggles."""

    source = raw if isinstance(raw, dict) else {}

    return {
        name: source.get(name) is True
        for name in EQUIPMENT_NAMES
    }
