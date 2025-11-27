"""Service 抽象基类。

提供服务层的基础功能和通用逻辑。
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.utils.logging import logger

if TYPE_CHECKING:
    from aurimyth.foundation_kit.repositories.base import BaseRepository


class BaseService(ABC):
    """Service 抽象基类。
    
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
        self._repositories: dict[str, BaseRepository] = {}
        logger.debug(f"初始化 {self.__class__.__name__}")
    
    @property
    def session(self) -> AsyncSession:
        """获取数据库会话。
        
        Returns:
            AsyncSession: 数据库会话
        """
        return self._session
    
    def register_repository(self, name: str, repository: BaseRepository) -> None:
        """注册Repository。
        
        Args:
            name: Repository名称
            repository: Repository实例
        """
        self._repositories[name] = repository
        logger.debug(f"{self.__class__.__name__} 注册 Repository: {name}")
    
    def get_repository(self, name: str) -> Optional[BaseRepository]:
        """获取Repository。
        
        Args:
            name: Repository名称
            
        Returns:
            Optional[BaseRepository]: Repository实例
        """
        return self._repositories.get(name)
    
    async def _validate(self, data: dict) -> dict:
        """数据验证（子类可重写）。
        
        Args:
            data: 要验证的数据
            
        Returns:
            dict: 验证后的数据
            
        Raises:
            ValidationError: 验证失败时抛出
        """
        return data
    
    async def _before_create(self, data: dict) -> dict:
        """创建前的钩子（子类可重写）。
        
        Args:
            data: 要创建的数据
            
        Returns:
            dict: 处理后的数据
        """
        return data
    
    async def _after_create(self, entity: object) -> None:
        """创建后的钩子（子类可重写）。
        
        Args:
            entity: 创建的实体
        """
        pass
    
    async def _before_update(self, entity: object, data: dict) -> dict:
        """更新前的钩子（子类可重写）。
        
        Args:
            entity: 要更新的实体
            data: 更新数据
            
        Returns:
            dict: 处理后的数据
        """
        return data
    
    async def _after_update(self, entity: object) -> None:
        """更新后的钩子（子类可重写）。
        
        Args:
            entity: 更新后的实体
        """
        pass
    
    async def _before_delete(self, entity: object) -> None:
        """删除前的钩子（子类可重写）。
        
        Args:
            entity: 要删除的实体
        """
        pass
    
    async def _after_delete(self, entity: object) -> None:
        """删除后的钩子（子类可重写）。
        
        Args:
            entity: 删除的实体
        """
        pass
    
    def __repr__(self) -> str:
        """字符串表示。"""
        repo_count = len(self._repositories)
        return f"<{self.__class__.__name__} repositories={repo_count}>"


__all__ = ["BaseService"]

