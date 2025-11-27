"""数据库迁移管理。"""

import asyncio

from alembic import command
from alembic.config import Config


async def run_migrations(script_location: str = "alembic.ini") -> None:
    alembic_cfg = Config(script_location)
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")


