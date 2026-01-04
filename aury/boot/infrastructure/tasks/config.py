"""任务队列配置。

Infrastructure 层配置数据类，由 application 层传入。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TaskConfig(BaseModel):
    """任务队列基础设施配置。
    
    纯数据类，由 application 层构造并传入 infrastructure 层。
    不直接读取环境变量。
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


__all__ = [
    "TaskConfig",
]



