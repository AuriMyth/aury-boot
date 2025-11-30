"""查询拦截器接口。

用于在查询执行前后执行自定义逻辑，如审计、日志记录等。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import Select


class QueryInterceptor(ABC):
    """查询拦截器接口。
    
    用于在查询执行前后执行自定义逻辑，如审计、日志记录等。
    
    用法:
        class AuditInterceptor(QueryInterceptor):
            async def before_query(self, query, **kwargs):
                logger.info(f"执行查询: {query}")
            
            async def after_query(self, result, **kwargs):
                logger.info(f"查询结果: {len(result)} 条记录")
    """
    
    @abstractmethod
    async def before_query(self, query: Select, **kwargs: Any) -> None:
        """查询执行前的钩子。
        
        Args:
            query: SQLAlchemy 查询对象
            **kwargs: 其他参数
        """
        pass
    
    @abstractmethod
    async def after_query(self, result: Any, **kwargs: Any) -> None:
        """查询执行后的钩子。
        
        Args:
            result: 查询结果
            **kwargs: 其他参数
        """
        pass

