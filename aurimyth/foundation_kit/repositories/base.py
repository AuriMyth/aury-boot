"""Repository 抽象基类和接口定义。

遵循面向对象设计原则：
- 单一职责原则：Repository只负责数据访问
- 依赖倒置原则：依赖抽象而非具体实现
- 开闭原则：对扩展开放，对修改关闭
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.base_models import BaseModel
from aurimyth.foundation_kit.utils.logging import logger

ModelType = TypeVar("ModelType", bound=BaseModel)


class IRepository(ABC, Generic[ModelType]):
    """Repository 接口定义。
    
    定义所有Repository必须实现的方法。
    遵循接口隔离原则，只定义必要的方法。
    """
    
    @abstractmethod
    async def get(self, id: int) -> Optional[ModelType]:
        """根据ID获取实体。"""
        pass
    
    @abstractmethod
    async def get_by(self, **filters) -> Optional[ModelType]:
        """根据条件获取单个实体。"""
        pass
    
    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100, **filters) -> List[ModelType]:
        """获取实体列表。"""
        pass
    
    @abstractmethod
    async def count(self, **filters) -> int:
        """统计实体数量。"""
        pass
    
    @abstractmethod
    async def exists(self, **filters) -> bool:
        """检查实体是否存在。"""
        pass
    
    @abstractmethod
    async def add(self, entity: ModelType) -> ModelType:
        """添加实体。"""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """创建实体。"""
        pass
    
    @abstractmethod
    async def update(self, entity: ModelType, data: Dict[str, Any]) -> ModelType:
        """更新实体。"""
        pass
    
    @abstractmethod
    async def delete(self, entity: ModelType, soft: bool = True) -> None:
        """删除实体。"""
        pass


class BaseRepository(IRepository[ModelType]):
    """Repository 抽象基类。
    
    提供通用的CRUD操作实现。
    子类可以重写这些方法以提供自定义行为。
    
    设计原则：
    - Repository 不执行 commit，只执行 flush
    - 事务由 Service 层通过装饰器管理
    - flush 会将更改发送到数据库但不提交
    
    Attributes:
        session: 数据库会话
        model_class: 模型类
    """
    
    def __init__(self, session: AsyncSession, model_class: Type[ModelType]) -> None:
        """初始化 Repository。
        
        Args:
            session: 数据库会话
            model_class: 模型类
        """
        self._session = session
        self._model_class = model_class
        logger.debug(f"初始化 {self.__class__.__name__}")
    
    @property
    def session(self) -> AsyncSession:
        """获取数据库会话。"""
        return self._session
    
    @property
    def model_class(self) -> Type[ModelType]:
        """获取模型类。"""
        return self._model_class
    
    def _build_base_query(self) -> Select:
        """构建基础查询，自动过滤软删除记录。
        
        Returns:
            Select: SQLAlchemy查询对象
        """
        query = select(self._model_class)
        if hasattr(self._model_class, "yn"):
            query = query.where(self._model_class.yn.is_(True))
        return query
    
    def _apply_filters(self, query: Select, **filters) -> Select:
        """应用过滤条件。
        
        Args:
            query: 查询对象
            **filters: 过滤条件
            
        Returns:
            Select: 应用过滤后的查询对象
        """
        for key, value in filters.items():
            if value is not None and hasattr(self._model_class, key):
                query = query.where(getattr(self._model_class, key) == value)
        return query
    
    async def get(self, id: int) -> Optional[ModelType]:
        """根据ID获取实体。
        
        Args:
            id: 实体ID
            
        Returns:
            Optional[ModelType]: 实体对象，不存在时返回None
        """
        query = self._build_base_query().where(self._model_class.id == id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by(self, **filters) -> Optional[ModelType]:
        """根据条件获取单个实体。
        
        Args:
            **filters: 过滤条件
            
        Returns:
            Optional[ModelType]: 实体对象，不存在时返回None
        """
        query = self._build_base_query()
        query = self._apply_filters(query, **filters)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """获取实体列表。
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            **filters: 过滤条件
            
        Returns:
            List[ModelType]: 实体列表
        """
        query = self._build_base_query()
        query = self._apply_filters(query, **filters)
        query = query.offset(skip).limit(limit)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def count(self, **filters) -> int:
        """统计实体数量。
        
        Args:
            **filters: 过滤条件
            
        Returns:
            int: 实体数量
        """
        query = select(func.count()).select_from(self._model_class)
        
        if hasattr(self._model_class, "yn"):
            query = query.where(self._model_class.yn.is_(True))
        
        query = self._apply_filters(query, **filters)
        
        result = await self._session.execute(query)
        return result.scalar_one()
    
    async def exists(self, **filters) -> bool:
        """检查实体是否存在。
        
        Args:
            **filters: 过滤条件
            
        Returns:
            bool: 是否存在
        """
        return await self.count(**filters) > 0
    
    async def add(self, entity: ModelType) -> ModelType:
        """添加实体（不提交）。
        
        Args:
            entity: 实体对象
            
        Returns:
            ModelType: 添加后的实体对象（包含生成的ID）
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        logger.debug(f"添加实体: {entity}")
        return entity
    
    async def create(self, data: Dict[str, Any]) -> ModelType:
        """创建实体（不提交）。
        
        Args:
            data: 实体数据字典
            
        Returns:
            ModelType: 创建的实体对象
        """
        entity = self._model_class(**data)
        return await self.add(entity)
    
    async def update(self, entity: ModelType, data: Dict[str, Any]) -> ModelType:
        """更新实体（不提交）。
        
        Args:
            entity: 要更新的实体对象
            data: 更新数据字典
            
        Returns:
            ModelType: 更新后的实体对象
        """
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        await self._session.flush()
        await self._session.refresh(entity)
        logger.debug(f"更新实体: {entity}")
        return entity
    
    async def delete(self, entity: ModelType, soft: bool = True) -> None:
        """删除实体（不提交）。
        
        Args:
            entity: 要删除的实体对象
            soft: 是否软删除（默认True）
        """
        if soft and hasattr(entity, "yn"):
            entity.yn = False
            await self._session.flush()
            logger.debug(f"软删除实体: {entity}")
        else:
            await self._session.delete(entity)
            await self._session.flush()
            logger.debug(f"硬删除实体: {entity}")
    
    async def delete_by_id(self, id: int, soft: bool = True) -> bool:
        """根据ID删除实体（不提交）。
        
        Args:
            id: 实体ID
            soft: 是否软删除（默认True）
            
        Returns:
            bool: 是否成功删除
        """
        entity = await self.get(id)
        if entity:
            await self.delete(entity, soft=soft)
            return True
        return False
    
    async def batch_create(self, data_list: List[Dict[str, Any]]) -> List[ModelType]:
        """批量创建实体（不提交）。
        
        Args:
            data_list: 实体数据列表
            
        Returns:
            List[ModelType]: 创建的实体列表
        """
        entities = [self._model_class(**data) for data in data_list]
        self._session.add_all(entities)
        await self._session.flush()
        
        for entity in entities:
            await self._session.refresh(entity)
        
        logger.debug(f"批量创建 {len(entities)} 个实体")
        return entities
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__} model={self._model_class.__name__}>"


class SimpleRepository:
    """简单Repository基类。
    
    适用于不需要泛型支持的简单场景。
    推荐使用 BaseRepository[ModelType]。
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """初始化 Repository。
        
        Args:
            session: 数据库会话
        """
        self._session = session
    
    @property
    def session(self) -> AsyncSession:
        """获取数据库会话。"""
        return self._session
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<{self.__class__.__name__}>"


__all__ = [
    "IRepository",
    "BaseRepository",
    "SimpleRepository",
]
