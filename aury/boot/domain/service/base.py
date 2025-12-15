"""领域服务基类。

提供业务服务层的基础功能和通用逻辑。
"""

from __future__ import annotations

from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.common.logging import logger
from aury.boot.infrastructure.monitoring import monitor


class BaseService(ABC):  # noqa: B024
    """领域服务抽象基类。
    
    职责：
    1. 管理数据库会话
    2. 协调多个Repository
    3. 实现业务逻辑
    4. 事务管理
    
    设计原则：
    - 单一职责：每个Service处理一个业务领域
    - 依赖注入：通过构造函数注入依赖
    - 事务管理：使用装饰器管理事务边界
    
    Attributes:
        session: 数据库会话
    
    使用示例:
        from aury.boot.domain.transaction import transactional
        
        class UserService(BaseService):
            def __init__(self, session: AsyncSession):
                super().__init__(session)
                self.user_repo = UserRepository(session)
                self.profile_repo = ProfileRepository(session)
            
            @transactional
            async def create_user_with_profile(self, data: dict):
                user = await self.user_repo.create(data["user"])
                profile = await self.profile_repo.create({
                    "user_id": user.id,
                    **data["profile"]
                })
                return user, profile
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """初始化Service。
        
        Args:
            session: 数据库会话
        """
        self._session = session
        logger.debug(f"初始化 {self.__class__.__name__}")
    
    @property
    def session(self) -> AsyncSession:
        """获取数据库会话。
        
        Returns:
            AsyncSession: 数据库会话
        """
        return self._session
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__}>"

