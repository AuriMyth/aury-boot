"""任务队列配置。

Infrastructure 层配置，不依赖 application 层。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TaskConfig(BaseSettings):
    """任务队列基础设施配置。
    
    Infrastructure 层直接使用的任务队列配置。
    
    环境变量前缀: TASK_
    示例: TASK_BROKER_URL, TASK_MAX_RETRIES
    """
    
    broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="任务队列Broker URL"
    )
    max_retries: int = Field(
        default=3,
        description="最大重试次数"
    )
    time_limit: int = Field(
        default=3600000,
        description="任务执行时间限制（毫秒）"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="TASK_",
        case_sensitive=False,
    )


__all__ = [
    "TaskConfig",
]



