"""事件总线配置。

提供事件系统的配置管理。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EventConfig(BaseSettings):
    """事件总线基础设施配置。
    
    Infrastructure 层直接使用的事件总线配置。
    
    环境变量前缀: EVENT_
    示例: EVENT_BROKER_URL, EVENT_EXCHANGE_NAME, EVENT_QUEUE_PREFIX, EVENT_MAX_HISTORY_SIZE
    """
    
    broker_url: str | None = Field(
        default=None,
        description="消息队列 URL（如 redis://localhost:6379/0 或 amqp://guest:guest@localhost:5672//），为空时使用本地模式"
    )
    exchange_name: str = Field(
        default="events",
        description="交换机名称"
    )
    queue_prefix: str = Field(
        default="event",
        description="队列名称前缀"
    )
    max_history_size: int | None = Field(
        default=1000,
        description="事件历史记录最大条数（None 表示不限制，生产环境建议设置或禁用历史记录）"
    )
    enable_history: bool = Field(
        default=True,
        description="是否启用事件历史记录（生产环境建议关闭以节省内存）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="EVENT_",
        case_sensitive=False,
    )


__all__ = [
    "EventConfig",
]


