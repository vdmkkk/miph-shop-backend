from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    alembic_ini = base_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    command.upgrade(config, "head")
