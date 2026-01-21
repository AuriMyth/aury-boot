"""分页和排序标准化模块。

提供统一的分页和排序参数定义，以及分页结果封装。
使用 Pydantic 2.5 进行数据验证和序列化。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaginationParams(BaseModel):
    """分页参数。
    
    使用 offset/limit 模式，与 SQL 语义一致。
    提供 `of()` 方法支持 page/size 风格的输入。
    
    示例:
        # 方式1: offset/limit（底层/API风格）
        params = PaginationParams(offset=20, limit=10)
        
        # 方式2: page/size（UI风格）
        params = PaginationParams.of(page=3, size=10)
    """
    
    offset: int = Field(default=0, ge=0, description="偏移量")
    limit: int = Field(default=20, ge=1, le=100, description="每页记录数，最大100")
    
    @classmethod
    def of(cls, page: int = 1, size: int = 20) -> "PaginationParams":
        """从 page/size 构造分页参数。
        
        Args:
            page: 页码，从 1 开始
            size: 每页记录数
            
        Returns:
            PaginationParams: 分页参数对象
            
        Raises:
            ValueError: 当 page < 1 或 size 无效时
        """
        if page < 1:
            raise ValueError("页码必须大于 0")
        return cls(offset=(page - 1) * size, limit=size)
    
    @property
    def page(self) -> int:
        """当前页码（从 1 开始）。"""
        if self.limit == 0:
            return 1
        return self.offset // self.limit + 1
    
    @property
    def size(self) -> int:
        """每页记录数（limit 的别名）。"""
        return self.limit


class SortParams(BaseModel):
    """排序参数。
    
    定义排序的字段和方向。
    
    支持两种语法：
    - 简洁语法: "-created_at" (前缀 - 表示降序)
    - 完整语法: "created_at:desc"
    
    示例:
        # 从字符串解析
        sort_params = SortParams.from_string("-created_at,priority")
        sort_params = SortParams.from_string("created_at:desc,priority:asc")
        
        # 带白名单验证
        sort_params = SortParams.from_string(
            "-created_at",
            allowed_fields={"id", "created_at", "priority"}
        )
        
        # 程序化构建
        sort_params = SortParams(sorts=[("-created_at",), ("priority", "asc")])
    """
    
    sorts: list[tuple[str, str]] = Field(default_factory=list, description="排序字段列表")
    
    @classmethod
    def from_string(
        cls,
        sort_str: str | None,
        *,
        allowed_fields: set[str] | None = None,
        default_direction: str = "asc",
    ) -> SortParams:
        """从字符串解析排序参数。
        
        支持两种语法：
        - 简洁语法: "-created_at" (前缀 - 表示降序)
        - 完整语法: "created_at:desc"
        
        Args:
            sort_str: 排序字符串，如 "-created_at,priority" 或 "created_at:desc,priority:asc"
            allowed_fields: 允许的字段白名单（可选，用于安全校验）
            default_direction: 默认排序方向（当不指定方向时使用）
            
        Returns:
            SortParams: 排序参数对象
            
        Raises:
            ValueError: 字段不在白名单中 或 方向无效
            
        示例:
            >>> SortParams.from_string("-created_at,priority")
            SortParams(sorts=[('created_at', 'desc'), ('priority', 'asc')])
            
            >>> SortParams.from_string("created_at:desc,priority:asc")
            SortParams(sorts=[('created_at', 'desc'), ('priority', 'asc')])
            
            >>> SortParams.from_string("-id", allowed_fields={"id", "name"})
            SortParams(sorts=[('id', 'desc')])
            
            >>> SortParams.from_string("-invalid", allowed_fields={"id", "name"})
            ValueError: 不允许的排序字段: invalid，允许的字段: id, name
        """
        if not sort_str:
            return cls(sorts=[])
        
        sorts = []
        for part in sort_str.split(","):
            part = part.strip()
            if not part:
                continue
            
            # 解析字段和方向
            if part.startswith("-"):
                # 简洁语法: -created_at
                field = part[1:]
                direction = "desc"
            elif ":" in part:
                # 完整语法: created_at:desc
                field, direction = part.split(":", 1)
            else:
                # 无方向指示，使用默认
                field = part
                direction = default_direction
            
            field = field.strip()
            direction = direction.strip().lower()
            
            # 字段白名单校验
            if allowed_fields and field not in allowed_fields:
                allowed_list = ", ".join(sorted(allowed_fields))
                raise ValueError(f"不允许的排序字段: {field}，允许的字段: {allowed_list}")
            
            # 方向校验
            if direction not in ("asc", "desc"):
                raise ValueError(f"排序方向必须是 'asc' 或 'desc'，得到: {direction}")
            
            sorts.append((field, direction))
        
        return cls(sorts=sorts)
    
    def add_sort(self, field: str, direction: str = "asc") -> None:
        """添加排序字段。
        
        Args:
            field: 字段名
            direction: 排序方向，asc 或 desc
        """
        if direction.lower() not in ("asc", "desc"):
            raise ValueError("排序方向必须是 'asc' 或 'desc'")
        self.sorts.append((field, direction.lower()))
    
    def add_sorts(self, *sorts: tuple[str, str]) -> None:
        """添加多个排序字段。
        
        Args:
            *sorts: 排序字段元组列表
        """
        for field, direction in sorts:
            self.add_sort(field, direction)
    
    @field_validator("sorts", mode="before")
    @classmethod
    def validate_sorts(cls, v: Any) -> list[tuple[str, str]]:
        """验证排序字段列表。
        
        Args:
            v: 排序字段列表
            
        Returns:
            list[tuple[str, str]]: 验证后的排序字段列表
        """
        if not v:
            return []
        
        result = []
        for item in v:
            if isinstance(item, str):
                # 如果是字符串，解析为字段和方向
                if item.startswith("-"):
                    field = item[1:]
                    direction = "desc"
                else:
                    field = item
                    direction = "asc"
                result.append((field, direction))
            elif isinstance(item, list | tuple) and len(item) == 2:
                field, direction = item
                if direction.lower() not in ("asc", "desc"):
                    raise ValueError(f"排序方向必须是 'asc' 或 'desc'，得到: {direction}")
                result.append((field, direction.lower()))
            else:
                raise ValueError(f"无效的排序参数: {item}")
        
        return result


class PaginationResult[ModelType](BaseModel):
    """分页结果。
    
    封装分页查询的结果，包括数据列表和分页信息。
    同时提供 offset/limit 和 page/size 两种风格的字段。
    """
    
    items: list[ModelType] = Field(description="数据列表")
    total: int = Field(ge=0, description="总记录数")
    offset: int = Field(ge=0, description="当前偏移量")
    limit: int = Field(ge=1, description="每页记录数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")
    
    @property
    def page(self) -> int:
        """当前页码（从 1 开始）。"""
        if self.limit == 0:
            return 1
        return self.offset // self.limit + 1
    
    @property
    def size(self) -> int:
        """每页记录数（limit 的别名）。"""
        return self.limit
    
    @property
    def total_pages(self) -> int:
        """总页数。"""
        if self.limit == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit
    
    @classmethod
    def create(
        cls,
        items: list[ModelType],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginationResult[ModelType]":
        """创建分页结果。
        
        Args:
            items: 数据列表
            total: 总记录数
            pagination: 分页参数
            
        Returns:
            PaginationResult[ModelType]: 分页结果
        """
        has_next = pagination.offset + pagination.limit < total
        has_prev = pagination.offset > 0
        
        return cls(
            items=items,
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
            has_next=has_next,
            has_prev=has_prev,
        )
    
    def get_next_params(self) -> PaginationParams | None:
        """获取下一页的分页参数。"""
        if not self.has_next:
            return None
        return PaginationParams(offset=self.offset + self.limit, limit=self.limit)
    
    def get_prev_params(self) -> PaginationParams | None:
        """获取上一页的分页参数。"""
        if not self.has_prev:
            return None
        new_offset = max(0, self.offset - self.limit)
        return PaginationParams(offset=new_offset, limit=self.limit)


class CursorPaginationParams(BaseModel):
    """游标分页参数。
    
    基于游标的分页，适用于大数据集和高性能场景。
    """
    
    cursor: str | None = Field(default=None, description="游标，用于定位数据位置")
    limit: int = Field(default=20, ge=1, le=100, description="每页记录数，最大100")
    direction: str = Field(default="next", description="分页方向：next 或 prev")
    
    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """验证分页方向。
        
        Args:
            v: 分页方向
            
        Returns:
            str: 验证后的分页方向
        """
        if v.lower() not in ("next", "prev"):
            raise ValueError("分页方向必须是 'next' 或 'prev'")
        return v.lower()


class CursorPaginationResult[ModelType](BaseModel):
    """游标分页结果。
    
    封装游标分页查询的结果。
    """
    
    items: list[ModelType] = Field(description="数据列表")
    next_cursor: str | None = Field(description="下一页游标")
    prev_cursor: str | None = Field(description="上一页游标")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")
    
    @classmethod
    def create(
        cls,
        items: list[ModelType],
        next_cursor: str | None = None,
        prev_cursor: str | None = None,
        limit: int = 20
    ) -> CursorPaginationResult[ModelType]:
        """创建游标分页结果。
        
        Args:
            items: 数据列表
            next_cursor: 下一页游标
            prev_cursor: 上一页游标
            limit: 每页记录数
            
        Returns:
            CursorPaginationResult[ModelType]: 游标分页结果
        """
        has_next = next_cursor is not None
        has_prev = prev_cursor is not None
        
        return cls(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_next=has_next,
            has_prev=has_prev,
        )


__all__ = [
    "CursorPaginationParams",
    "CursorPaginationResult",
    "PaginationParams",
    "PaginationResult",
    "SortParams",
]
