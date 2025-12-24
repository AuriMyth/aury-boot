"""数据库事务管理工具。

提供多种事务管理方式：
1. @transactional - 通用装饰器，自动从参数中获取session
2. @requires_transaction - Repository 事务检查装饰器
3. transactional_context - 上下文管理器（支持 on_commit 回调）
4. TransactionManager - 手动控制事务（支持 Savepoints）
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
import contextvars
from functools import wraps
from inspect import signature
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.common.logging import logger
from aury.boot.domain.exceptions import TransactionRequiredError

# 用于跟踪嵌套事务的上下文变量
_transaction_depth: contextvars.ContextVar[int] = contextvars.ContextVar("transaction_depth", default=0)

# 用于存储 on_commit 回调的上下文变量（不设置 default，避免可变对象问题）
_on_commit_callbacks: contextvars.ContextVar[list[Callable[[], Any] | Callable[[], Awaitable[Any]]] | None] = (
    contextvars.ContextVar("on_commit_callbacks", default=None)
)


def on_commit(callback: Callable[[], Any] | Callable[[], Awaitable[Any]]) -> None:
    """注册事务提交后执行的回调函数。
    
    类似 Django 的 transaction.on_commit()，回调会在事务成功提交后执行。
    如果事务回滚，回调不会执行。
    
    Args:
        callback: 回调函数，可以是同步或异步函数
    
    用法:
        async with transactional_context(session):
            order = await repo.create({...})
            on_commit(lambda: send_notification.delay(order.id))
            # 只有事务提交成功后，才会执行 send_notification
    
    注意:
        - 回调在事务提交后、上下文退出前执行
        - 如果回调抛出异常，不会影响事务（事务已提交）
        - 嵌套事务中注册的回调，只在最外层事务提交后执行
    """
    callbacks = _on_commit_callbacks.get()
    if callbacks is None:
        callbacks = []
        _on_commit_callbacks.set(callbacks)
    callbacks.append(callback)


async def _execute_on_commit_callbacks() -> None:
    """执行所有 on_commit 回调。"""
    callbacks = _on_commit_callbacks.get()
    if not callbacks:
        return
    
    # 清空回调列表
    _on_commit_callbacks.set(None)
    
    for callback in callbacks:
        try:
            result = callback()
            # 如果是协程，await 它
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:
            # 回调异常不影响事务（事务已提交），只记录日志
            logger.error(f"on_commit 回调执行失败: {exc}")


@asynccontextmanager
async def transactional_context(session: AsyncSession, auto_commit: bool = True) -> AsyncGenerator[AsyncSession]:
    """
    事务上下文管理器，自动处理提交和回滚。
    
    Args:
        session: 数据库会话
        auto_commit: 是否自动提交（默认True）
    
    特性:
        - 支持嵌套调用：只有最外层会 commit/rollback
        - 兼容 SQLAlchemy 2.0 autobegin 模式
        - 支持 on_commit 回调
    
    用法:
        async with transactional_context(session):
            await repo1.create(...)
            await repo2.update(...)
            on_commit(lambda: print("事务已提交"))
            # 成功自动提交，异常自动回滚
    """
    # 使用 contextvars 跟踪嵌套深度，避免依赖 in_transaction()
    depth = _transaction_depth.get()
    is_outermost = depth == 0
    _transaction_depth.set(depth + 1)
    
    # 最外层事务初始化回调列表
    if is_outermost:
        _on_commit_callbacks.set(None)
    
    try:
        yield session
        # 只有最外层且 auto_commit=True 时才提交
        if auto_commit and is_outermost:
            await session.commit()
            logger.debug("事务提交成功")
            # 提交成功后执行 on_commit 回调
            await _execute_on_commit_callbacks()
    except Exception as exc:
        # 只有最外层才回滚
        if is_outermost:
            await session.rollback()
            # 回滚时清空回调列表（不执行）
            _on_commit_callbacks.set(None)
            logger.error(f"事务回滚: {exc}")
        raise
    finally:
        _transaction_depth.set(depth)


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

        # 使用事务上下文管理器，它会自动处理嵌套情况
        logger.debug(f"执行事务 {func.__name__}")
        async with transactional_context(session):
            return await func(*args, **kwargs)

    return wrapper


class TransactionManager:
    """
    事务管理器，提供更细粒度的事务控制。
    
    支持功能：
    - 手动控制事务 begin/commit/rollback
    - Savepoints（保存点）
    - on_commit 回调
    
    用法:
        tm = TransactionManager(session)
        
        await tm.begin()
        try:
            await repo1.create(data)
            
            # 使用 Savepoint
            sid = await tm.savepoint()
            try:
                await repo2.update(data)
            except Exception:
                await tm.savepoint_rollback(sid)
            
            await tm.commit()
        except Exception:
            await tm.rollback()
            raise
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction = None
        self._savepoints: dict[str, Any] = {}  # savepoint_id -> nested transaction
        self._savepoint_counter = 0
        self._on_commit_callbacks: list[Callable[[], Any] | Callable[[], Awaitable[Any]]] = []
    
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
            # 执行 on_commit 回调
            await self._execute_callbacks()
    
    async def rollback(self):
        """回滚事务。"""
        if self._transaction:
            await self.session.rollback()
            self._transaction = None
            self._savepoints.clear()
            self._on_commit_callbacks.clear()  # 回滚时清空回调
            logger.debug("手动回滚事务")
    
    async def savepoint(self, name: str | None = None) -> str:
        """创建保存点。
        
        Args:
            name: 保存点名称，可选。如果不提供，自动生成。
        
        Returns:
            str: 保存点 ID，用于后续 commit 或 rollback
        
        用法:
            sid = await tm.savepoint()
            try:
                await risky_operation()
                await tm.savepoint_commit(sid)
            except Exception:
                await tm.savepoint_rollback(sid)
        """
        self._savepoint_counter += 1
        savepoint_id = name or f"sp_{self._savepoint_counter}"
        
        # 使用 begin_nested() 创建 savepoint
        nested = await self.session.begin_nested()
        self._savepoints[savepoint_id] = nested
        logger.debug(f"创建保存点: {savepoint_id}")
        return savepoint_id
    
    async def savepoint_commit(self, savepoint_id: str) -> None:
        """提交保存点。
        
        Args:
            savepoint_id: savepoint() 返回的 ID
        """
        if savepoint_id not in self._savepoints:
            logger.warning(f"保存点不存在: {savepoint_id}")
            return
        
        # SQLAlchemy 的 begin_nested() 在退出时自动提交
        # 这里只需要从字典中移除
        del self._savepoints[savepoint_id]
        logger.debug(f"确认保存点: {savepoint_id}")
    
    async def savepoint_rollback(self, savepoint_id: str) -> None:
        """回滚到保存点。
        
        Args:
            savepoint_id: savepoint() 返回的 ID
        """
        if savepoint_id not in self._savepoints:
            logger.warning(f"保存点不存在: {savepoint_id}")
            return
        
        nested = self._savepoints.pop(savepoint_id)
        await nested.rollback()
        logger.debug(f"回滚到保存点: {savepoint_id}")
    
    def on_commit(self, callback: Callable[[], Any] | Callable[[], Awaitable[Any]]) -> None:
        """注册事务提交后执行的回调。
        
        Args:
            callback: 回调函数，可以是同步或异步函数
        """
        self._on_commit_callbacks.append(callback)
    
    async def _execute_callbacks(self) -> None:
        """执行所有 on_commit 回调。"""
        callbacks = self._on_commit_callbacks
        self._on_commit_callbacks = []
        
        for callback in callbacks:
            try:
                result = callback()
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                logger.error(f"on_commit 回调执行失败: {exc}")
    
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


def requires_transaction(func: Callable) -> Callable:
    """事务必需装饰器。
    
    确保方法在事务中执行，如果不在事务中则抛出 TransactionRequiredError。
    
    用于 Repository 方法，强制要求在事务中调用。
    
    用法:
        class UserRepository(BaseRepository):
            @requires_transaction
            async def update_user(self, user, data):
                # 此方法必须在事务中执行
                return await self.update(user, data)
    """
    
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._session.in_transaction():
            raise TransactionRequiredError(
                f"方法 {func.__name__} 需要在事务中执行，但当前会话不在事务中"
            )
        return await func(self, *args, **kwargs)
    
    return wrapper


__all__ = [
    "TransactionManager",
    "TransactionRequiredError",
    "_transaction_depth",  # 内部使用，不对外文档化
    "ensure_transaction",
    "on_commit",
    "requires_transaction",
    "transactional",
    "transactional_context",
]

