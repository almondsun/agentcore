"""Identity normalization helpers."""


def normalize_user_id(raw: str) -> str:
    value = raw.strip().lower()
    if not value:
        raise ValueError("user id must not be blank")
    return value
