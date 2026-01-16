from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from core.config import settings

_MIGRATION_LOCK_ID = 987654321


def run_migrations() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    alembic_ini = base_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    sync_url = settings.database_url.replace("asyncpg", "psycopg")
    engine = create_engine(sync_url, pool_pre_ping=True)

    connection = engine.connect()
    try:
        locked = connection.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _MIGRATION_LOCK_ID},
        ).scalar()
        if not locked:
            return
        command.upgrade(config, "head")
        connection.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": _MIGRATION_LOCK_ID},
        )
    finally:
        connection.close()
        engine.dispose()
