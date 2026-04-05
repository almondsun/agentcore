"""CLI formatting helpers."""

from tiny_medium.identity import normalize_user_id


def format_summary_line(user_id: str, status: str) -> str:
    return f"{normalize_user_id(user_id)}:{status.strip()}"
