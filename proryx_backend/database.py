"""
Database configuration for ProRyx Property Management System.

Implements two-level multi-tenancy with account_id + company_id.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import (
    UUID,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    declared_attr,
    mapped_column,
)
from sqlalchemy.sql import func

from .config import settings
from .core.database_types import UUID as UUID_DB

logger = logging.getLogger(__name__)

# Create async engine with SSL support for MySQL
connect_args = {}
if settings.database_url.startswith("mysql+asyncmy"):
    connect_args = {
        "ssl": {
            "ssl_check_hostname": settings.database_ssl_check_hostname,
            "ssl_verify_cert": settings.database_ssl_verify_cert,
            "ssl_verify_identity": settings.database_ssl_verify_identity,
        },
    }

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class
Base = declarative_base()


class TimestampMixin:
    """Mixin to add created and updated timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AccountScoped:
    """Mixin for account + company scoped models (two-level multi-tenancy).

    This mixin implements a two-level SaaS multi-tenancy model:
    - account_id: Top-level tenant (SaaS account)
    - company_id: Second-level tenant (company within account)

    Models using this mixin will have:
    - Composite primary key: (account_id, company_id, id)
    - Automatic tenant filtering via session context
    - Account+Company-scoped unique constraints
    """

    # Account ID (top-level tenant)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    # Company ID (second-level tenant within account)
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    # ID within the account+company scope
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        nullable=False,
    )

    # UUID for external references (unique within account+company)
    uuid: Mapped[UUID] = mapped_column(UUID_DB(), nullable=False, index=True)

    @declared_attr
    def __table_args__(cls):
        """Add account+company-scoped unique constraint on UUID."""
        return (
            UniqueConstraint(
                "account_id",
                "company_id",
                "uuid",
                name=f"uq_{cls.__tablename__}_acct_comp_uuid",
            ),
        )


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_next_id_for_tenant(
    session: AsyncSession, model_class, account_id: int, company_id: int
) -> int:
    """Get the next available ID for a table within an account+company scope.

    Args:
        session: Async database session
        model_class: SQLAlchemy model class
        account_id: Account ID
        company_id: Company ID

    Returns:
        Next available ID for the tenant
    """
    table_name = model_class.__tablename__

    result = await session.execute(
        text(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name} "
            f"WHERE account_id = :account_id AND company_id = :company_id"
        ),
        {"account_id": account_id, "company_id": company_id},
    )
    return result.scalar()


@event.listens_for(AccountScoped, "before_insert", propagate=True)
def set_composite_key_fields(mapper, connection, target):
    """Event listener to set composite key fields before insert."""
    import uuid

    # Generate UUID if not set
    if not hasattr(target, "uuid") or target.uuid is None:
        target.uuid = uuid.uuid4()

    # Generate ID if not set
    if (
        target.id is None
        and target.account_id is not None
        and target.company_id is not None
    ):
        table_name = mapper.mapped_table.name

        result = connection.execute(
            text(
                f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name} "
                f"WHERE account_id = :account_id AND company_id = :company_id"
            ),
            {"account_id": target.account_id, "company_id": target.company_id},
        )
        next_id = result.scalar()
        target.id = next_id


class TenantFilteredSession:
    """Wrapper to apply tenant filtering to queries."""

    def __init__(self, session: AsyncSession, account_id: int, company_id: int):
        self._session = session
        self._account_id = account_id
        self._company_id = company_id
        self._session.info["account_id"] = account_id
        self._session.info["company_id"] = company_id

    async def execute(self, statement, params=None, **kwargs):
        """Execute with automatic tenant filtering."""
        from sqlalchemy.sql import Select

        if isinstance(statement, Select) and self._account_id is not None:
            org_scoped_models = []
            for mapper in Base.registry.mappers:
                if (
                    hasattr(mapper.class_, "__mro__")
                    and AccountScoped in mapper.class_.__mro__
                ):
                    org_scoped_models.append(mapper.class_)

            from sqlalchemy.sql.util import find_tables

            tables_in_query = set(find_tables(statement, include_aliases=True))

            for model in org_scoped_models:
                if hasattr(model, "__table__") and model.__table__ in tables_in_query:
                    statement = statement.filter(
                        model.account_id == self._account_id,
                        model.company_id == self._company_id,
                    )

        return await self._session.execute(statement, params, **kwargs)

    def add(self, instance):
        return self._session.add(instance)

    def add_all(self, instances):
        return self._session.add_all(instances)

    async def flush(self):
        return await self._session.flush()

    async def commit(self):
        return await self._session.commit()

    async def rollback(self):
        return await self._session.rollback()

    async def close(self):
        return await self._session.close()

    @property
    def info(self):
        return self._session.info

    def __getattr__(self, name):
        return getattr(self._session, name)


async def get_tenant_db(
    request: Request, session: AsyncSession = Depends(get_db)
) -> AsyncSession:
    """Get a tenant-aware database session.

    The account_id and company_id are extracted from request.state (set by auth middleware).
    """
    from fastapi import HTTPException

    if not hasattr(request.state, "account_id") or not hasattr(
        request.state, "company_id"
    ):
        raise HTTPException(
            status_code=403,
            detail="Tenant context not available. Please authenticate first.",
        )

    account_id = request.state.account_id
    company_id = request.state.company_id

    return TenantFilteredSession(session, account_id, company_id)


# Type alias for dependency injection
TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]


async def init_db():
    """Initialize database tables."""
    from .modules.auth import models as auth_models  # noqa: F401
    from .modules.property_management import models as property_models  # noqa: F401
    from .modules.tenant_management import models as tenant_models  # noqa: F401
    from .modules.vendor_management import models as vendor_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
