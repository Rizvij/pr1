"""Common utilities for ProRyx backend."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def sanitize_string(value: str | None, max_length: int = 255) -> str | None:
    """Sanitize a string value by stripping whitespace and truncating."""
    if value is None:
        return None
    value = value.strip()
    if len(value) > max_length:
        return value[:max_length]
    return value


def generate_code(prefix: str, id: int, padding: int = 6) -> str:
    """Generate a business code like PROP-000001."""
    return f"{prefix}-{str(id).zfill(padding)}"
