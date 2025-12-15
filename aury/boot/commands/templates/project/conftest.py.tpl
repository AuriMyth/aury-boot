"""Pytest 配置和 fixtures。"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.infrastructure.database import DatabaseManager


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话。"""
    db_manager = DatabaseManager.get_instance()
    async with db_manager.session() as session:
        yield session
        await session.rollback()
