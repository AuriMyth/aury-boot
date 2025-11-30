"""查询构建器。

提供链式查询和复杂条件构建功能。

注意：此模块定义在 domain 层（而非 infrastructure），因为查询构建是领域层的通用能力，
与特定的数据库实现无关。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Select, and_, not_, or_, select
from sqlalchemy.orm import joinedload, selectinload

from aurimyth.foundation_kit.domain.models import Base

# 操作符处理函数字典（函数式编程）
_OPERATOR_HANDLERS: dict[str, Callable[[Any, Any], Any]] = {
    "gt": lambda field, value: field > value,
    "lt": lambda field, value: field < value,
    "gte": lambda field, value: field >= value,
    "lte": lambda field, value: field <= value,
    "in": lambda field, value: field.in_(value),
    "like": lambda field, value: field.like(value),
    "ilike": lambda field, value: field.ilike(value),
    "ne": lambda field, value: field != value,
}


def _handle_isnull_operator(field: Any, value: bool) -> Any:
    """处理 isnull 操作符。
    
    Args:
        field: 字段对象
        value: 是否为空（True=为空，False=不为空）
        
    Returns:
        SQLAlchemy 条件表达式
    """
    if value:
        return field.is_(None)
    return field.isnot(None)


class QueryBuilder[ModelType: Base]:
    """查询构建器。
    
    提供链式查询和复杂条件构建功能。
    支持操作符：__gt、__lt、__gte、__lte、__in、__like、__ilike、__isnull、__ne
    支持复杂条件：and_()、or_()、not_()
    支持关系查询：joinedload()、selectinload()
    """
    
    def __init__(self, model_class: type[ModelType]) -> None:
        """初始化查询构建器。
        
        Args:
            model_class: 模型类
        """
        self._model_class = model_class
        self._query = select(model_class)
        self._filters = []
        self._order_by = []
        self._load_options = []
        self._limit = None
        self._offset = None
    
    def filter(self, **kwargs) -> QueryBuilder[ModelType]:
        """添加过滤条件。
        
        支持操作符：
        - __gt: 大于
        - __lt: 小于
        - __gte: 大于等于
        - __lte: 小于等于
        - __in: 包含于
        - __like: 模糊匹配（区分大小写）
        - __ilike: 模糊匹配（不区分大小写）
        - __isnull: 是否为空
        - __ne: 不等于
        
        Args:
            **kwargs: 过滤条件
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        for key, value in kwargs.items():
            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
                if not hasattr(self._model_class, field_name):
                    continue
                    
                field = getattr(self._model_class, field_name)
                
                # 使用函数式编程处理操作符
                if operator == "isnull":
                    # isnull 需要特殊处理（需要判断 value 的布尔值）
                    self._filters.append(_handle_isnull_operator(field, value))
                elif operator in _OPERATOR_HANDLERS:
                    # 使用函数字典处理其他操作符
                    handler = _OPERATOR_HANDLERS[operator]
                    self._filters.append(handler(field, value))
            else:
                if hasattr(self._model_class, key) and value is not None:
                    self._filters.append(getattr(self._model_class, key) == value)
        
        return self
    
    def filter_by(self, *conditions) -> QueryBuilder[ModelType]:
        """添加自定义过滤条件。
        
        Args:
            *conditions: SQLAlchemy 条件表达式
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        self._filters.extend(conditions)
        return self
    
    @staticmethod
    def and_(*conditions) -> Any:
        """创建 AND 条件。
        
        Args:
            *conditions: 条件列表
            
        Returns:
            SQLAlchemy AND 表达式
        """
        return and_(*conditions)
    
    @staticmethod
    def or_(*conditions) -> Any:
        """创建 OR 条件。
        
        Args:
            *conditions: 条件列表
            
        Returns:
            SQLAlchemy OR 表达式
        """
        return or_(*conditions)
    
    @staticmethod
    def not_(condition) -> Any:
        """创建 NOT 条件。
        
        Args:
            condition: 条件表达式
            
        Returns:
            SQLAlchemy NOT 表达式
        """
        return not_(condition)
    
    def order_by(self, *fields) -> QueryBuilder[ModelType]:
        """添加排序条件。
        
        支持字符串字段名，使用 "-" 前缀表示降序。
        
        Args:
            *fields: 排序字段列表
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        for field in fields:
            if isinstance(field, str):
                if field.startswith("-"):
                    field_name = field[1:]
                    if hasattr(self._model_class, field_name):
                        self._order_by.append(getattr(self._model_class, field_name).desc())
                else:
                    if hasattr(self._model_class, field):
                        self._order_by.append(getattr(self._model_class, field))
            else:
                self._order_by.append(field)
        
        return self
    
    def limit(self, limit: int) -> QueryBuilder[ModelType]:
        """设置返回记录数限制。
        
        Args:
            limit: 记录数
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        self._limit = limit
        return self
    
    def offset(self, offset: int) -> QueryBuilder[ModelType]:
        """设置跳过记录数。
        
        Args:
            offset: 跳过记录数
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        self._offset = offset
        return self
    
    def joinedload(self, *relationships) -> QueryBuilder[ModelType]:
        """添加关联加载（JOIN）。
        
        Args:
            *relationships: 关联关系列表
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        for rel in relationships:
            if isinstance(rel, str):
                if hasattr(self._model_class, rel):
                    self._load_options.append(joinedload(getattr(self._model_class, rel)))
            else:
                self._load_options.append(joinedload(rel))
        
        return self
    
    def selectinload(self, *relationships) -> QueryBuilder[ModelType]:
        """添加关联加载（SELECT IN）。
        
        Args:
            *relationships: 关联关系列表
            
        Returns:
            QueryBuilder: 查询构建器实例
        """
        for rel in relationships:
            if isinstance(rel, str):
                if hasattr(self._model_class, rel):
                    self._load_options.append(selectinload(getattr(self._model_class, rel)))
            else:
                self._load_options.append(selectinload(rel))
        
        return self
    
    def build(self) -> Select:
        """构建查询对象。
        
        Returns:
            Select: SQLAlchemy 查询对象
        """
        query = self._query
        
        # 应用过滤条件
        if self._filters:
            query = query.where(and_(*self._filters))
        
        # 应用排序
        if self._order_by:
            query = query.order_by(*self._order_by)
        
        # 应用关联加载
        if self._load_options:
            query = query.options(*self._load_options)
        
        # 应用分页
        if self._offset is not None:
            query = query.offset(self._offset)
        
        if self._limit is not None:
            query = query.limit(self._limit)
        
        return query


__all__ = [
    "QueryBuilder",
]


