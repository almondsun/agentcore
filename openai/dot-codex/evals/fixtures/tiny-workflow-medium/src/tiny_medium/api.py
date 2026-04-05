"""API-facing summary helpers."""

from tiny_medium.identity import normalize_user_id
from tiny_medium.status import normalize_status


def summarize_user(user_id: str, status: str) -> dict[str, str]:
    return {
        "id": normalize_user_id(user_id),
        "status": normalize_status(status),
    }
