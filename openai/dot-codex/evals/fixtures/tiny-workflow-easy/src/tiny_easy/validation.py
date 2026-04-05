"""Validation helpers for retry configuration."""


def parse_retry_delay(raw: str | int) -> int:
    """Parse a retry delay in seconds from an int or string value."""
    if isinstance(raw, int):
        delay = raw
    else:
        text = raw.strip()
        delay = int(text or "0")

    if delay < 0:
        raise ValueError("retry delay must be zero or greater")
    return delay
