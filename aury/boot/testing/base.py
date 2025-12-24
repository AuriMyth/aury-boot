"""测试基类。

提供类似 Django TestCase 的功能，自动处理数据库事务回滚。
"""

from __future__ import annotations

from abc import ABC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.common.logging import logger
from aury.boot.infrastructure.database.manager import DatabaseManager


class TestCase(ABC):  # noqa: B024
    """测试基类。
    
    提供类似 Django TestCase 的功能：
    - 自动数据库事务回滚
    - setUp/tearDown 钩子
    - 测试客户端支持
    - Fixtures 支持
    
    使用示例:
        class UserServiceTest(TestCase):
            async def setUp(self):
                self.db = await DatabaseManager.get_session()
                self.user_repo = UserRepository(self.db)
            
            async def test_create_user(self):
                user = await self.user_repo.create({"name": "张三"})
                assert user.name == "张三"
    """
    
    def __init__(self) -> None:
        """初始化测试用例。"""
        self._db_session: AsyncSession | None = None
        self._db_manager: DatabaseManager | None = None
    
    @property
    def db(self) -> AsyncSession:
        """获取数据库会话。
        
        Returns:
            AsyncSession: 数据库会话
            
        Raises:
            RuntimeError: 如果会话未初始化
        """
        if self._db_session is None:
            raise RuntimeError("数据库会话未初始化，请在 setUp 中调用 await self.setup_db()")
        return self._db_session
    
    async def setup_db(self) -> AsyncSession:
        """设置数据库会话（在事务中）。
        
        Returns:
            AsyncSession: 数据库会话
        """
        if self._db_manager is None:
            self._db_manager = DatabaseManager.get_instance()
            if not hasattr(self._db_manager, '_initialized') or not self._db_manager._initialized:
                await self._db_manager.initialize()
        
        # 使用 session_factory 创建会话
        self._db_session = self._db_manager.session_factory()
        # 开始事务（测试结束后会自动回滚）
        await self._db_session.begin()
        logger.debug("测试数据库会话已创建（事务模式）")
        return self._db_session
    
    async def setUp(self) -> None:  # noqa: B027
        """测试前准备（子类可重写）。
        
        在此方法中初始化测试所需的资源。
        """
        pass
    
    async def tearDown(self) -> None:  # noqa: B027
        """测试后清理（子类可重写）。
        
        在此方法中清理测试资源。
        """
        pass
    
    async def _cleanup(self) -> None:
        """内部清理方法，自动回滚事务。"""
        if self._db_session:
            try:
                await self._db_session.rollback()
                logger.debug("测试事务已回滚")
            except Exception as e:
                logger.error(f"回滚测试事务失败: {e}")
            finally:
                await self._db_session.close()
                self._db_session = None
        
        if self._db_manager:
            await self._db_manager.cleanup()
            self._db_manager = None


# Pytest fixtures 支持
@pytest.fixture
async def test_case():
    """Pytest fixture，提供测试用例实例。"""
    case = TestCase()
    await case.setUp()
    try:
        yield case
    finally:
        await case.tearDown()
        await case._cleanup()


@pytest.fixture
async def db_session(test_case: TestCase):
    """Pytest fixture，提供数据库会话。"""
    await test_case.setup_db()
    return test_case.db
