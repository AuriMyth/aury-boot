"""数据库管理器 - 命名多实例实现。

提供统一的数据库连接管理、会话创建和健康检查功能。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from aury.boot.common.logging import logger


class DatabaseManager:
    """数据库管理器（命名多实例）。
    
    职责：
    1. 管理数据库引擎和连接池
    2. 提供会话工厂
    3. 健康检查和重连机制
    4. 生命周期管理
    5. 支持多个命名实例，如主库/从库、不同业务数据库等
    
    使用示例:
        # 默认实例
        db_manager = DatabaseManager.get_instance()
        await db_manager.initialize()
        
        # 命名实例
        primary = DatabaseManager.get_instance("primary")
        replica = DatabaseManager.get_instance("replica")
        
        # 获取会话
        async with db_manager.session() as session:
            # 使用 session 进行数据库操作
            pass
        
        # 清理
        await db_manager.cleanup()
    """
    
    _instances: dict[str, DatabaseManager] = {}
    
    def __init__(self, name: str = "default") -> None:
        """初始化数据库管理器。
        
        Args:
            name: 实例名称
        """
        self.name = name
        self._initialized: bool = False
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None
        self._max_retries: int = 3
        self._retry_delay: float = 1.0
    
    @classmethod
    def get_instance(cls, name: str = "default") -> DatabaseManager:
        """获取指定名称的实例。
        
        Args:
            name: 实例名称，默认为 "default"
            
        Returns:
            DatabaseManager: 数据库管理器实例
        """
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]
    
    @classmethod
    def reset_instance(cls, name: str | None = None) -> None:
        """重置实例（仅用于测试）。
        
        Args:
            name: 要重置的实例名称。如果为 None，则重置所有实例。
            
        注意：调用此方法前应先调用 cleanup() 释放资源。
        """
        if name is None:
            cls._instances.clear()
        elif name in cls._instances:
            del cls._instances[name]
    
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
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化。"""
        return self._initialized
    
    async def initialize(
        self,
        url: str | None = None,
        *,
        echo: bool | None = None,
        pool_size: int | None = None,
        max_overflow: int | None = None,
        pool_timeout: int | None = None,
        pool_recycle: int | None = None,
        isolation_level: str | None = None,
    ) -> None:
        """初始化数据库连接。
        
        Args:
            url: 数据库连接字符串，默认从配置读取
            echo: 是否打印SQL语句
            pool_size: 连接池大小
            max_overflow: 最大溢出连接数
            pool_timeout: 连接超时时间（秒）
            pool_recycle: 连接回收时间（秒）
            isolation_level: 事务隔离级别
        """
        if self._initialized:
            logger.warning("数据库管理器已初始化，跳过重复初始化")
            return
        
        # 使用提供的参数或环境变量默认值
        import os
        database_url = url or os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "数据库 URL 未配置。请通过以下方式之一提供："
                "1. 通过 initialize(url=...) 参数传入"
                "2. 设置环境变量 DATABASE_URL"
            )
        db_echo = echo if echo is not None else os.getenv("DB_ECHO", "false").lower() == "true"
        db_pool_size = pool_size or int(os.getenv("DB_POOL_SIZE", "5"))
        db_max_overflow = max_overflow or int(os.getenv("DB_MAX_OVERFLOW", "10"))
        db_pool_timeout = pool_timeout or int(os.getenv("DB_POOL_TIMEOUT", "30"))
        db_pool_recycle = pool_recycle or int(os.getenv("DB_POOL_RECYCLE", "1800"))
        db_isolation_level = isolation_level or os.getenv("DATABASE_ISOLATION_LEVEL")
        
        # 构建引擎参数
        engine_kwargs: dict = {
            "echo": db_echo,
            "future": True,
            "pool_pre_ping": True,
            "pool_size": db_pool_size,
            "max_overflow": db_max_overflow,
            "pool_timeout": db_pool_timeout,
            "pool_recycle": db_pool_recycle,
        }
        
        # 添加隔离级别（如果配置了）
        if db_isolation_level:
            engine_kwargs["isolation_level"] = db_isolation_level
            logger.info(f"事务隔离级别设置为: {db_isolation_level}")
        
        self._engine = create_async_engine(database_url, **engine_kwargs)
        
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
        
        使用 SQLAlchemy 的通用异常类，支持所有数据库后端。
        
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
            except (DisconnectionError, OperationalError) as exc:
                logger.warning(f"数据库连接丢失，剩余重试次数: {retries}, 错误: {exc}")
                retries -= 1
                if retries == 0:
                    logger.error("数据库连接重试失败")
                    raise
                await asyncio.sleep(self._retry_delay)
            except Exception as exc:
                # 其他异常直接抛出，不重试
                logger.error(f"数据库连接检查失败: {exc}")
                raise
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
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
    
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """FastAPI 依赖注入专用的会话获取器。
        
        Yields:
            AsyncSession: 数据库会话
            
        使用示例（FastAPI 路由）:
            @router.get("/items")
            async def get_items(
                session: AsyncSession = Depends(db_manager.get_session),
            ):
                ...
        """
        async with self.session() as session:
            yield session
    
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

