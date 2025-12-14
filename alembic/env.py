"""
Alembic environment configuration for ProRyx.

Supports async MySQL with SQLAlchemy 2.0.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Load the CONFIG environment variable for YAML config
config_path = os.getenv("CONFIG", "resources/config/local.yaml")

# Import settings and models
# We need to set CONFIG before importing anything from proryx_backend
os.environ.setdefault("CONFIG", config_path)

from proryx_backend.config import settings  # noqa: E402
from proryx_backend.database import Base  # noqa: E402

# Import all models to ensure they are registered with Base.metadata
from proryx_backend.modules.auth import models as auth_models  # noqa: E402, F401
from proryx_backend.modules.property_management import (  # noqa: E402, F401
    models as property_models,
)
from proryx_backend.modules.tenant_management import (  # noqa: E402, F401
    models as tenant_models,
)
from proryx_backend.modules.vendor_management import (  # noqa: E402, F401
    models as vendor_models,
)

# Alembic Config object
config = context.config

# Override sqlalchemy.url with value from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Build connect args for SSL (MySQL)
    connect_args = {}
    db_url = settings.database_url
    if db_url.startswith("mysql+asyncmy"):
        connect_args = {
            "ssl": {
                "ssl_check_hostname": settings.database_ssl_check_hostname,
                "ssl_verify_cert": settings.database_ssl_verify_cert,
                "ssl_verify_identity": settings.database_ssl_verify_identity,
            },
        }

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
