"""仓储接口定义。

定义所有Repository必须实现的接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from aury.boot.domain.models import GUID, Base
from aury.boot.domain.pagination import PaginationParams, PaginationResult, SortParams

if TYPE_CHECKING:
    from typing import Self

    from aury.boot.domain.repository.query_builder import QueryBuilder


class IRepository[ModelType: Base](ABC):
    """仓储接口定义。
    
    定义所有Repository必须实现的方法。
    遵循接口隔离原则，只定义必要的方法。
    """
    
    @abstractmethod
    async def get(self, id: int | GUID) -> ModelType | None:
        """根据ID获取实体。支持 int 和 GUID。"""
        pass
    
    @abstractmethod
    async def get_by(self, **filters) -> ModelType | None:
        """根据条件获取单个实体。"""
        pass
    
    @abstractmethod
    async def list(self, skip: int = 0, limit: int | None = 100, **filters) -> list[ModelType]:
        """获取实体列表。limit=None 时返回全部记录（谨慎使用）。"""
        pass
    
    @abstractmethod
    async def paginate(
        self,
        pagination_params: PaginationParams,
        sort_params: SortParams | None = None,
        **filters
    ) -> PaginationResult[ModelType]:
        """分页获取实体列表。
        
        Args:
            pagination_params: 分页参数
            sort_params: 排序参数
            **filters: 过滤条件
            
        Returns:
            PaginationResult[ModelType]: 分页结果
        """
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
    async def create(self, data: dict[str, Any]) -> ModelType:
        """创建实体。"""
        pass
    
    @abstractmethod
    async def update(self, entity: ModelType, data: dict[str, Any]) -> ModelType:
        """更新实体。"""
        pass
    
    @abstractmethod
    async def delete(self, entity: ModelType, soft: bool = True) -> None:
        """删除实体。"""
        pass
    
    @abstractmethod
    def query(self) -> QueryBuilder[ModelType]:
        """创建查询构建器。"""
        pass
    
    @abstractmethod
    def with_commit(self) -> Self:
        """返回强制提交的 Repository 视图。
        
        在 auto_commit=False 时，使用此方法可以强制单次操作提交。
        
        Returns:
            Self: 带强制提交标记的 Repository 副本
        """
        pass

