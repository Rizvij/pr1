"""Authentication models for ProRyx.

Implements two-level multi-tenancy:
- Account: Top-level SaaS tenant
- Company: Second-level tenant within an account
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ...core.database_types import UUID as UUID_DB
from ...database import AccountScoped, Base, TimestampMixin


class Account(TimestampMixin, Base):
    """Top-level SaaS account.

    An account represents a tenant organization that can have multiple companies.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(UUID_DB(), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name={self.name})>"


class Company(TimestampMixin, Base):
    """Company within an account (second-level tenant).

    A company is a subdivision within an account. Users and data are scoped
    to both account_id and company_id.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(UUID_DB(), unique=True, nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="companies")

    __table_args__ = (Index("ix_companies_account", "account_id"),)

    def __repr__(self) -> str:
        return (
            f"<Company(id={self.id}, name={self.name}, account_id={self.account_id})>"
        )


class RoleSlug(str, enum.Enum):
    """Available user roles."""

    ADMIN = "admin"
    MANAGER = "manager"
    LEASING = "leasing"
    OPERATIONS = "operations"
    FINANCE = "finance"
    VIEWER = "viewer"


class Role(Base):
    """User roles (simple role-based access control)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Role(slug={self.slug}, name={self.name})>"


class User(AccountScoped, TimestampMixin, Base):
    """User within account + company scope."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("roles.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role")

    __table_args__ = (
        Index("ix_users_email", "account_id", "company_id", "email", unique=True),
        Index("ix_users_account_company", "account_id", "company_id"),
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class RefreshToken(Base):
    """Refresh tokens for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index(
            "ix_refresh_tokens_user", "user_account_id", "user_company_id", "user_id"
        ),
        Index("ix_refresh_tokens_hash", "token_hash"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
