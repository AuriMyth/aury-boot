"""应用配置。

配置优先级：命令行参数 > 环境变量 > .env 文件 > 默认值

环境变量格式（使用双下划线分层）：
    DATABASE__URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
    CACHE__CACHE_TYPE=redis
    CACHE__URL=redis://localhost:6379/0
    LOG__LEVEL=INFO
"""

from aury.boot.application.config import BaseConfig


class AppConfig(BaseConfig):
    """{project_name} 配置。
    
    继承 BaseConfig 获得所有默认配置项：
    - server: 服务器配置 (SERVER__*)
    - database: 数据库配置 (DATABASE__*)
    - cache: 缓存配置 (CACHE__*)
    - log: 日志配置 (LOG__*)
    - migration: 迁移配置 (MIGRATION__*)
    
    可以在这里添加自定义配置项。
    """
    
    # 添加自定义配置项
    # my_setting: str = Field(default="value", description="自定义配置")
    pass
