"""UPSERT 策略实现。

为不同数据库提供 UPSERT 操作的策略实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sqlalchemy import Table, text
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.common.logging import logger


class UpsertStrategy(ABC):
    """UPSERT 策略抽象基类。
    
    为不同数据库提供 UPSERT 操作的统一接口。
    """
    
    @abstractmethod
    async def execute(
        self,
        session: AsyncSession,
        table: Table,
        data_list: list[dict[str, Any]],
        index_elements: list[str],
        update_columns: list[str],
    ) -> None:
        """执行 UPSERT 操作。
        
        Args:
            session: 数据库会话
            table: 表对象
            data_list: 数据字典列表
            index_elements: 索引字段列表
            update_columns: 需要更新的字段列表
        """
        pass


class PostgreSQLUpsertStrategy(UpsertStrategy):
    """PostgreSQL UPSERT 策略。
    
    使用 ON CONFLICT DO UPDATE 语法。
    """
    
    async def execute(
        self,
        session: AsyncSession,
        table: Table,
        data_list: list[dict[str, Any]],
        index_elements: list[str],
        update_columns: list[str],
    ) -> None:
        """执行 PostgreSQL UPSERT。"""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        stmt = pg_insert(table).values(data_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={col: stmt.excluded[col] for col in update_columns}
        )
        
        await session.execute(stmt)
        await session.flush()
        logger.debug(f"批量插入或更新 {len(data_list)} 条记录（PostgreSQL）")


class SQLiteUpsertStrategy(UpsertStrategy):
    """SQLite UPSERT 策略。
    
    使用 ON CONFLICT DO UPDATE 语法（SQLite 3.24.0+）。
    """
    
    async def execute(
        self,
        session: AsyncSession,
        table: Table,
        data_list: list[dict[str, Any]],
        index_elements: list[str],
        update_columns: list[str],
    ) -> None:
        """执行 SQLite UPSERT。"""
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        
        stmt = sqlite_insert(table).values(data_list)
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={col: stmt.excluded[col] for col in update_columns}
        )
        
        await session.execute(stmt)
        await session.flush()
        logger.debug(f"批量插入或更新 {len(data_list)} 条记录（SQLite）")


class MySQLUpsertStrategy(UpsertStrategy):
    """MySQL UPSERT 策略。
    
    使用 ON DUPLICATE KEY UPDATE 语法。
    """
    
    async def execute(
        self,
        session: AsyncSession,
        table: Table,
        data_list: list[dict[str, Any]],
        index_elements: list[str],
        update_columns: list[str],
    ) -> None:
        """执行 MySQL UPSERT。"""
        # 构建批量 INSERT ... ON DUPLICATE KEY UPDATE 语句
        columns = list(data_list[0].keys())
        column_names = ", ".join(columns)
        
        # 构建 VALUES 子句（批量插入）
        values_placeholders = []
        params = {}
        for idx, data in enumerate(data_list):
            row_placeholders = []
            for col in columns:
                param_name = f"{col}_{idx}"
                row_placeholders.append(f":{param_name}")
                params[param_name] = data[col]
            values_placeholders.append(f"({', '.join(row_placeholders)})")
        
        values_clause = ", ".join(values_placeholders)
        
        # 构建 ON DUPLICATE KEY UPDATE 子句
        update_clauses = [f"{col} = VALUES({col})" for col in update_columns]
        update_clause = ", ".join(update_clauses)
        
        # 执行 SQL
        sql = f"INSERT INTO {table.name} ({column_names}) VALUES {values_clause} ON DUPLICATE KEY UPDATE {update_clause}"
        await session.execute(text(sql), params)
        await session.flush()
        logger.debug(f"批量插入或更新 {len(data_list)} 条记录（MySQL）")


class UpsertStrategyFactory:
    """UPSERT 策略工厂。
    
    根据数据库方言创建相应的策略实例。
    """
    
    _strategies: ClassVar[dict[str, type[UpsertStrategy]]] = {
        "postgresql": PostgreSQLUpsertStrategy,
        "sqlite": SQLiteUpsertStrategy,
        "mysql": MySQLUpsertStrategy,
    }
    
    @classmethod
    def create(cls, dialect_name: str) -> UpsertStrategy:
        """创建 UPSERT 策略实例。
        
        Args:
            dialect_name: 数据库方言名称
            
        Returns:
            UpsertStrategy: 策略实例
            
        Raises:
            NotImplementedError: 如果数据库不支持 UPSERT 操作
        """
        strategy_class = cls._strategies.get(dialect_name)
        if strategy_class is None:
            raise NotImplementedError(
                f"数据库 {dialect_name} 不支持 UPSERT 操作。"
                "请使用 bulk_insert() 或实现自定义的插入/更新逻辑。"
            )
        
        return strategy_class()
    
    @classmethod
    def register(cls, dialect_name: str, strategy_class: type[UpsertStrategy]) -> None:
        """注册自定义策略。
        
        Args:
            dialect_name: 数据库方言名称
            strategy_class: 策略类
        """
        cls._strategies[dialect_name] = strategy_class
        logger.debug(f"注册 UPSERT 策略: {dialect_name} -> {strategy_class.__name__}")


__all__ = [
    "MySQLUpsertStrategy",
    "PostgreSQLUpsertStrategy",
    "SQLiteUpsertStrategy",
    "UpsertStrategy",
    "UpsertStrategyFactory",
]



