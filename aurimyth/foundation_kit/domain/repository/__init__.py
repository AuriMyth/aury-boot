"""仓储模块 - 接口、实现和工具。

提供：
- IRepository: 仓储接口
- BaseRepository: 通用 CRUD 实现
- QueryBuilder: 查询构建器
- QueryInterceptor: 查询拦截器
"""

from .impl import BaseRepository, SimpleRepository
from .interceptors import QueryInterceptor
from .interface import IRepository
from .query_builder import QueryBuilder

__all__ = [
    "BaseRepository",
    "IRepository",
    "QueryBuilder",
    "QueryInterceptor",
    "SimpleRepository",
]


