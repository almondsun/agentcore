"""Shared status normalization."""

_STATUS_TABLE = {
    "active": ("active", "Active"),
    "enabled": ("active", "Active"),
    "disabled": ("disabled", "Disabled"),
    "suspended": ("suspended", "Suspended"),
}


def normalize_status(raw: str) -> str:
    value = raw.strip().lower()
    if value not in _STATUS_TABLE:
        raise ValueError(f"unknown status: {raw}")
    return _STATUS_TABLE[value][0]


def display_status(code: str) -> str:
    for normalized_code, label in _STATUS_TABLE.values():
        if normalized_code == code:
            return label
    raise ValueError(f"unknown status code: {code}")
