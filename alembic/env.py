import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import settings to get dynamic database URL
from app.core.config import get_settings

# Import all models so Alembic can detect them for autogenerate
from app.models.base import Base
from app.models.ignored_issue_type import IgnoredIssueType  # noqa: F401
from app.models.ignored_ticket import IgnoredTicket  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.team_member import TeamMember  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_project import UserProject  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get dynamic database URL from app config
try:
    settings = get_settings()
    db_url = settings.db_url
except Exception as e:
    # Fallback to alembic.ini if config loading fails
    db_url = config.get_main_option("sqlalchemy.url")
    print(f"⚠️  Warning: Could not load app config, using alembic.ini DB URL: {db_url}")
    print(f"   Error: {e}")

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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
