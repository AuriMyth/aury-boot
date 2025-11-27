"""数据库管理器 - 单例模式实现。

提供统一的数据库连接管理、会话创建和健康检查功能。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from aurimyth.foundation_kit.core.config import DatabaseSettings
from aurimyth.foundation_kit.utils.logging import logger


class DatabaseManager:
    """数据库管理器（单例模式）。
    
    职责：
    1. 管理数据库引擎和连接池
    2. 提供会话工厂
    3. 健康检查和重连机制
    4. 生命周期管理
    
    使用示例:
        # 初始化
        db_manager = DatabaseManager.get_instance()
        await db_manager.initialize()
        
        # 获取会话
        async with db_manager.session() as session:
            # 使用 session 进行数据库操作
            pass
        
        # 清理
        await db_manager.cleanup()
    """
    
    _instance: Optional[DatabaseManager] = None
    _initialized: bool = False
    _config: Optional[DatabaseSettings] = None
    
    def __init__(self) -> None:
        """私有构造函数，使用 get_instance() 获取实例。"""
        if DatabaseManager._instance is not None:
            raise RuntimeError("DatabaseManager 是单例类，请使用 get_instance() 获取实例")
        
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._max_retries: int = 3
        self._retry_delay: float = 1.0
    
    @classmethod
    def get_instance(cls) -> DatabaseManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def configure(cls, config: DatabaseSettings) -> None:
        """配置数据库管理器。
        
        Args:
            config: 数据库配置
        """
        cls._config = config
    
    @property
    def engine(self) -> AsyncEngine:
        """获取数据库引擎。"""
        if self._engine is None:
            raise RuntimeError("数据库管理器未初始化，请先调用 initialize()")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """获取会话工厂。"""
        if self._session_factory is None:
            raise RuntimeError("数据库管理器未初始化，请先调用 initialize()")
        return self._session_factory
    
    async def initialize(
        self,
        url: Optional[str] = None,
        *,
        echo: Optional[bool] = None,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        pool_timeout: Optional[int] = None,
        pool_recycle: Optional[int] = None,
    ) -> None:
        """初始化数据库连接。
        
        Args:
            url: 数据库连接字符串，默认从配置读取
            echo: 是否打印SQL语句
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 连接超时时间（秒）
            pool_recycle: 连接回收时间（秒）
        """
        if self._initialized:
            logger.warning("数据库管理器已初始化，跳过重复初始化")
            return
        
        # 使用提供的参数或配置中的默认值
        if self._config is not None:
            database_url = url or self._config.url
            db_echo = echo if echo is not None else self._config.echo
            db_pool_size = pool_size or self._config.pool_size
            db_max_overflow = max_overflow or self._config.max_overflow
            db_pool_timeout = pool_timeout or self._config.pool_timeout
            db_pool_recycle = pool_recycle or self._config.pool_recycle
        else:
            # 如果没有配置，使用环境变量或默认值
            import os
            database_url = url or os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/aurimyth")
            db_echo = echo if echo is not None else os.getenv("DB_ECHO", "false").lower() == "true"
            db_pool_size = pool_size or int(os.getenv("DB_POOL_SIZE", "5"))
            db_max_overflow = max_overflow or int(os.getenv("DB_MAX_OVERFLOW", "10"))
            db_pool_timeout = pool_timeout or int(os.getenv("DB_POOL_TIMEOUT", "30"))
            db_pool_recycle = pool_recycle or int(os.getenv("DB_POOL_RECYCLE", "1800"))
        
        self._engine = create_async_engine(
            database_url,
            echo=db_echo,
            future=True,
            pool_pre_ping=True,
            pool_size=db_pool_size,
            max_overflow=db_max_overflow,
            pool_timeout=db_pool_timeout,
            pool_recycle=db_pool_recycle,
        )
        
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )
        
        # 验证连接
        await self.health_check()
        
        self._initialized = True
        logger.info("数据库管理器初始化完成")
    
    async def health_check(self) -> bool:
        """健康检查。
        
        Returns:
            bool: 连接是否正常
        """
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.debug("数据库健康检查通过")
            return True
        except Exception as exc:
            logger.error(f"数据库健康检查失败: {exc}")
            return False
    
    async def _check_session_connection(self, session: AsyncSession) -> None:
        """检查会话连接状态，必要时重连。
        
        Args:
            session: 数据库会话
            
        Raises:
            Exception: 重试次数耗尽后抛出异常
        """
        retries = self._max_retries
        while retries > 0:
            try:
                await session.execute(text("SELECT 1"))
                return
            except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                    asyncpg.exceptions.InterfaceError) as exc:
                logger.warning(f"数据库连接丢失，剩余重试次数: {retries}, 错误: {exc}")
                retries -= 1
                if retries == 0:
                    logger.error("数据库连接重试失败")
                    raise
                await asyncio.sleep(self._retry_delay)
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（上下文管理器）。
        
        Yields:
            AsyncSession: 数据库会话
            
        使用示例:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        session = self.session_factory()
        try:
            await self._check_session_connection(session)
            yield session
        except Exception as exc:
            await session.rollback()
            logger.exception(f"数据库会话异常: {exc}")
            raise
        finally:
            await session.close()
    
    async def create_session(self) -> AsyncSession:
        """创建新的数据库会话（需要手动关闭）。
        
        Returns:
            AsyncSession: 数据库会话
            
        注意：使用后需要手动调用 await session.close()
        建议使用 session() 上下文管理器代替此方法。
        """
        session = self.session_factory()
        await self._check_session_connection(session)
        return session
    
    async def cleanup(self) -> None:
        """清理资源，关闭所有连接。"""
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("数据库连接已关闭")
        
        self._engine = None
        self._session_factory = None
        self._initialized = False
    
    def __repr__(self) -> str:
        """字符串表示。"""
        status = "initialized" if self._initialized else "not initialized"
        return f"<DatabaseManager status={status}>"


__all__ = [
    "DatabaseManager",
]
