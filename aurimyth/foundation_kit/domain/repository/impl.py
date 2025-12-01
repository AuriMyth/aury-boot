"""Domain 层仓储实现 - BaseRepository 的具体实现。

提供通用的 CRUD 操作实现，是 IRepository 接口的具体实现。

**重要架构决策**：本模块在 domain 层实现了 IRepository 接口。
Infrastructure 层现在仅负责数据库连接管理，完全不依赖 domain 层。
"""

from __future__ import annotations

import time
from typing import Any, Union, cast

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.domain.exceptions import VersionConflictError
from aurimyth.foundation_kit.domain.models import GUID, Base
from aurimyth.foundation_kit.domain.pagination import (
    PaginationParams,
    PaginationResult,
    SortParams,
)
from aurimyth.foundation_kit.domain.repository.interface import IRepository
from aurimyth.foundation_kit.domain.repository.query_builder import QueryBuilder


def _get_model_attr(model_class: type, attr_name: str) -> Any:
    """安全地获取模型类的属性，避免类型检查器警告。
    
    Args:
        model_class: SQLAlchemy 模型类
        attr_name: 属性名称
        
    Returns:
        属性值（如果存在），否则返回 None
    """
    return cast(Any, getattr(model_class, attr_name, None))


class BaseRepository[ModelType: Base](IRepository[ModelType]):
    """仓储基类实现。提供通用 CRUD 操作。
    
    **重要**：使用此类的模型必须至少继承以下 Mixin 之一：
    - IDMixin: 标准自增整数主键
    - UUIDMixin: UUID 主键
    
    可选 Mixin：
    - AuditableStateMixin: 软删除支持
    - VersionMixin: 乐观锁支持
    - TimestampMixin: 时间戳字段
    
    示例：
        class User(IDMixin, TimestampMixin, AuditableStateMixin, Base):
            __tablename__ = "users"
            name: Mapped[str]
    """
    
    def __init__(self, session: AsyncSession, model_class: type[ModelType]) -> None:
        self._session = session
        self._model_class = model_class
        logger.debug(f"初始化 {self.__class__.__name__}")
    
    @property
    def session(self) -> AsyncSession:
        return self._session
    
    @property
    def model_class(self) -> type[ModelType]:
        return self._model_class
    
    def query(self) -> QueryBuilder[ModelType]:
        builder = QueryBuilder(self._model_class)
        if hasattr(self._model_class, "deleted_at"):
            deleted_at = _get_model_attr(self._model_class, "deleted_at")
            builder.filter_by(deleted_at == 0)
        return builder
    
    def _build_base_query(self) -> Select:
        query = select(self._model_class)
        if hasattr(self._model_class, "deleted_at"):
            deleted_at = _get_model_attr(self._model_class, "deleted_at")
            query = query.where(deleted_at == 0)
        return query
    
    def _apply_filters(self, query: Select, **filters) -> Select:
        for key, value in filters.items():
            if value is not None and hasattr(self._model_class, key):
                query = query.where(getattr(self._model_class, key) == value)
        return query
    
    async def get(self, id: Union[int, GUID]) -> ModelType | None:
        """按 ID 获取实体，支持 int 和 GUID。"""
        if not hasattr(self._model_class, "id"):
            raise AttributeError(f"模型 {self._model_class.__name__} 没有 'id' 字段，请继承 IDMixin 或 UUIDMixin")
        id_attr = _get_model_attr(self._model_class, "id")
        query = self._build_base_query().where(id_attr == id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by(self, **filters) -> ModelType | None:
        query = self._build_base_query()
        query = self._apply_filters(query, **filters)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def list(self, skip: int = 0, limit: int = 100, **filters) -> list[ModelType]:
        query = self._build_base_query()
        query = self._apply_filters(query, **filters)
        query = query.offset(skip).limit(limit)
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def paginate(
        self,
        pagination_params: PaginationParams,
        sort_params: SortParams | None = None,
        **filters
    ) -> PaginationResult[ModelType]:
        query = self._build_base_query()
        query = self._apply_filters(query, **filters)
        
        if sort_params:
            order_by_list = []
            for field, direction in sort_params.sorts:
                field_attr = getattr(self._model_class, field, None)
                if field_attr is not None:
                    if direction == "desc":
                        order_by_list.append(field_attr.desc())
                    else:
                        order_by_list.append(field_attr)
            if order_by_list:
                query = query.order_by(*order_by_list)
        
        query = query.offset(pagination_params.offset).limit(pagination_params.limit)
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        total_count = await self.count(**filters)
        
        return PaginationResult.create(
            items=items,
            total=total_count,
            pagination_params=pagination_params,
        )
    
    async def count(self, **filters) -> int:
        query = select(func.count()).select_from(self._model_class)
        if hasattr(self._model_class, "deleted_at"):
            deleted_at = _get_model_attr(self._model_class, "deleted_at")
            query = query.where(deleted_at == 0)
        query = self._apply_filters(query, **filters)
        result = await self._session.execute(query)
        return result.scalar_one()
    
    async def exists(self, **filters) -> bool:
        return await self.count(**filters) > 0
    
    async def add(self, entity: ModelType) -> ModelType:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        logger.debug(f"添加实体: {entity}")
        return entity
    
    async def create(self, data: dict[str, Any]) -> ModelType:
        entity = self._model_class(**data)
        return await self.add(entity)
    
    async def update(self, entity: ModelType, data: dict[str, Any] | None = None) -> ModelType:
        if hasattr(entity, "version"):
            entity_any = cast(Any, entity)
            current_version = entity_any.version
            await self._session.refresh(entity, ["version"])
            if entity_any.version != current_version:
                raise VersionConflictError(
                    message="数据已被其他操作修改，请刷新后重试",
                    current_version=entity_any.version,
                    expected_version=current_version,
                )
            entity_any.version = entity_any.version + 1
        
        if data:
            for key, value in data.items():
                if hasattr(entity, key) and key != "version":
                    setattr(entity, key, value)
        
        await self._session.flush()
        await self._session.refresh(entity)
        logger.debug(f"更新实体: {entity}")
        return entity
    
    async def delete(self, entity: ModelType, soft: bool = True) -> None:
        if soft:
            if hasattr(entity, "deleted_at"):
                # 使用 setattr 因为类型检查器不知道动态属性
                setattr(entity, "deleted_at", int(time.time()))  # noqa: B010
                await self._session.flush()
                logger.debug(f"软删除实体: {entity}")
            elif hasattr(entity, "mark_deleted"):
                entity.mark_deleted()
                await self._session.flush()
                logger.debug(f"软删除实体（使用方法）: {entity}")
            else:
                await self._session.delete(entity)
                await self._session.flush()
                logger.debug(f"硬删除实体（无软删除字段）: {entity}")
        else:
            await self._session.delete(entity)
            await self._session.flush()
            logger.debug(f"硬删除实体: {entity}")
    
    async def mark_deleted(self, entity: ModelType) -> None:
        await self.delete(entity, soft=True)
    
    async def hard_delete(self, entity: ModelType) -> None:
        await self.delete(entity, soft=False)
    
    async def delete_by_id(self, id: int, soft: bool = True) -> bool:
        entity = await self.get(id)
        if entity:
            await self.delete(entity, soft=soft)
            return True
        return False
    
    async def batch_create(self, data_list: list[dict[str, Any]]) -> list[ModelType]:
        entities = [self._model_class(**data) for data in data_list]
        self._session.add_all(entities)
        await self._session.flush()
        for entity in entities:
            await self._session.refresh(entity)
        logger.debug(f"批量创建 {len(entities)} 个实体")
        return entities
    
    async def bulk_insert(self, data_list: list[dict[str, Any]]) -> None:
        if not data_list:
            return
        await self._session.execute(
            self._model_class.__table__.insert(),
            data_list
        )
        await self._session.flush()
        logger.debug(f"批量插入 {len(data_list)} 条记录")
    
    async def bulk_update(self, data_list: list[dict[str, Any]],
                         index_elements: list[str] | None = None) -> None:
        if not data_list:
            return
        if index_elements is None:
            index_elements = ["id"]
        for data in data_list:
            for field in index_elements:
                if field not in data:
                    raise ValueError(f"批量更新数据缺少索引字段: {field}")
        await self._session.bulk_update_mappings(self._model_class, data_list)
        await self._session.flush()
        logger.debug(f"批量更新 {len(data_list)} 条记录")
    
    async def bulk_delete(self, filters: dict[str, Any] | None = None) -> int:
        query = delete(self._model_class)
        if hasattr(self._model_class, "deleted_at"):
            deleted_at = _get_model_attr(self._model_class, "deleted_at")
            query = query.where(deleted_at == 0)
        if filters:
            for key, value in filters.items():
                if hasattr(self._model_class, key) and value is not None:
                    attr = _get_model_attr(self._model_class, key)
                    query = query.where(attr == value)
        result = await self._session.execute(query)
        await self._session.flush()
        deleted_count = cast(Any, result).rowcount
        logger.debug(f"批量删除 {deleted_count} 条记录")
        return deleted_count
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self._model_class.__name__}>"


class SimpleRepository:
    """简单Repository基类。"""
    
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
    
    @property
    def session(self) -> AsyncSession:
        return self._session
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


__all__ = ["BaseRepository", "SimpleRepository"]
