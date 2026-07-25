import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Make the project root importable (alembic runs from backend/).
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import Base  # noqa: E402

# Import every model so it registers with Base.metadata BEFORE autogenerate reads
# it — otherwise a table not imported here is silently dropped from migrations.
# Same set and order as main.py's lifespan (Achievement before User: the User
# relationship references it).
from backend.models import (  # noqa: E402,F401
    achievement,
    user,
    lesson,
    test_result,
    study_plan,
    flashcard,
    topic,
    conversation_session,
    exercise,
    sync_event,
)

target_metadata = Base.metadata


def _database_url() -> str:
    """Resolve the migration target: DATABASE_URL (env / .env) wins over the
    static ini value, so the same migrations run against SQLite locally and
    PostgreSQL in deployment without editing alembic.ini."""
    from backend.config import settings
    return settings.DATABASE_URL or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (URL only, no DBAPI)."""
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (real Engine + connection)."""
    url = _database_url()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot ALTER most columns in place; batch mode rebuilds the
            # table instead. No-op on PostgreSQL.
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
