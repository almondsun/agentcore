from .normalize import normalize_user_id


def lookup_user(user_id: str) -> str:
    normalized = normalize_user_id(user_id)
    return f"user:{normalized}"
