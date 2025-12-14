"""Custom database types for MySQL."""

import uuid

from sqlalchemy import String, TypeDecorator


class UUID(TypeDecorator):
    """UUID type for MySQL.

    Stores UUIDs as CHAR(36) strings in MySQL.
    Automatically converts between Python uuid.UUID objects and strings.
    """

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert UUID to string when saving to database."""
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        """Convert string to UUID when reading from database."""
        if value is None:
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        return value
