"""数据库事务管理工具。

提供多种事务管理方式：
1. @transactional - 通用装饰器，自动从参数中获取session
2. transactional_context - 上下文管理器
3. TransactionManager - 手动控制事务
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import wraps
from inspect import signature

from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.domain.exceptions import TransactionRequiredError


@asynccontextmanager
async def transactional_context(session: AsyncSession, auto_commit: bool = True) -> AsyncGenerator[AsyncSession]:
    """
    事务上下文管理器，自动处理提交和回滚。
    
    Args:
        session: 数据库会话
        auto_commit: 是否自动提交（默认True）
    
    用法:
        async with transactional_context(session):
            # 在这里执行多个数据库操作
            await repo1.create(...)
            await repo2.update(...)
            # 如果没有异常，自动提交
            # 如果有异常，自动回滚
    """
    # 检查是否已在事务中（支持嵌套）
    already_in_transaction = session.in_transaction()
    
    try:
        yield session
        # 只有在非嵌套且auto_commit=True时才提交
        if auto_commit and not already_in_transaction:
            await session.commit()
            logger.debug("事务提交成功")
    except Exception as exc:
        # 发生异常时回滚
        if not already_in_transaction:
            await session.rollback()
            logger.error(f"事务回滚: {exc}")
        raise


def transactional[T](func: Callable[..., T]) -> Callable[..., T]:
    """
    通用事务装饰器，自动从函数参数中查找session并管理事务。
    
    支持多种用法：
    1. 参数名为 session 的函数
    2. 参数名为 db 的函数
    3. 类方法中有 self.session 属性
    
    特性：
    - 自动识别session参数
    - 成功时自动提交
    - 异常时自动回滚
    - 支持嵌套（内层事务不会重复提交）
    
    用法示例:
        @transactional
        async def create_user(session: AsyncSession, name: str):
            # 操作会在事务中执行
            user = User(name=name)
            session.add(user)
            await session.flush()
            return user
        
        # 或者在类方法中
        class UserService:
            def __init__(self, session: AsyncSession):
                self.session = session
            
            @transactional
            async def create_with_profile(self, name: str):
                # 自动使用 self.session
                user = await self.create_user(name)
                profile = await self.create_profile(user.id)
                return user, profile
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        session: AsyncSession | None = None
        
        # 策略1: 从kwargs中获取session或db
        if "session" in kwargs:
            session = kwargs["session"]
        elif "db" in kwargs:
            session = kwargs["db"]
        else:
            # 策略2: 从args中获取 (检查类型注解)
            sig = signature(func)
            params = list(sig.parameters.keys())
            
            for i, param_name in enumerate(params):
                if i < len(args):
                    param_value = args[i]
                    # 检查是否是AsyncSession类型
                    if isinstance(param_value, AsyncSession):
                        session = param_value
                        break
                    # 检查参数名
                    if param_name in ("session", "db"):
                        session = param_value
                        break
            
            # 策略3: 从self.session获取 (类方法)
            if session is None and args and hasattr(args[0], "session"):
                session = args[0].session

        if session is None:
            raise ValueError(
                f"无法找到session参数。请确保函数 {func.__name__} 有一个名为 'session' 或 'db' 的参数，"
                "或者类有 'session' 属性。"
            )

        # 检查是否已经在事务中
        if session.in_transaction():
            logger.debug(f"已在事务中，直接执行 {func.__name__}")
            return await func(*args, **kwargs)

        # 否则开启新事务
        logger.debug(f"开启新事务执行 {func.__name__}")
        async with transactional_context(session):
            return await func(*args, **kwargs)

    return wrapper


class TransactionManager:
    """
    事务管理器，提供更细粒度的事务控制。
    
    用法:
        tm = TransactionManager(session)
        
        await tm.begin()
        try:
            await repo1.create(data)
            await repo2.update(data)
            await tm.commit()
        except Exception:
            await tm.rollback()
            raise
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction = None
    
    async def begin(self):
        """开始事务。"""
        if self._transaction is None:
            self._transaction = await self.session.begin()
            logger.debug("手动开启事务")
    
    async def commit(self):
        """提交事务。"""
        if self._transaction:
            await self.session.commit()
            self._transaction = None
            logger.debug("手动提交事务")
    
    async def rollback(self):
        """回滚事务。"""
        if self._transaction:
            await self.session.rollback()
            self._transaction = None
            logger.debug("手动回滚事务")
    
    async def __aenter__(self):
        await self.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()


def ensure_transaction(session: AsyncSession) -> bool:
    """
    检查当前会话是否在事务中。
    
    用于在Repository中进行安全检查。
    """
    return session.in_transaction()


__all__ = [
    "TransactionManager",
    "TransactionRequiredError",
    "ensure_transaction",
    "transactional",
    "transactional_context",
]

