"""JWT service for ProRyx authentication."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from ...config import settings

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
REFRESH_TOKEN_REMEMBER_ME_DAYS = 30


def create_access_token(
    user_id: int,
    account_id: int,
    company_id: int,
    email: str,
    role_slug: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": str(user_id),
        "account_id": account_id,
        "company_id": company_id,
        "email": email,
        "role": role_slug,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token(remember_me: bool = False) -> tuple[str, datetime]:
    """Create a refresh token.

    Returns:
        Tuple of (token_string, expiry_datetime)
    """
    token = secrets.token_urlsafe(32)
    if remember_me:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_REMEMBER_ME_DAYS
        )
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    return token, expires_at


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Returns:
        Token payload if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_expiry_seconds(remember_me: bool = False) -> int:
    """Get access token expiry in seconds."""
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60
