# 5. 高级配置管理

## 配置体系

Kit 使用 Pydantic 的 `BaseSettings` 实现分层配置管理。

### 基础配置类

```python
# config.py
from aury.boot.application.config import BaseConfig
from pydantic import Field

class AppConfig(BaseConfig):
    """应用配置"""
    
    # 业务配置
    app_name: str = Field(default="My Service", description="应用名称")
    max_retries: int = Field(default=3, description="最大重试次数")
    cache_ttl: int = Field(default=3600, description="缓存过期时间（秒）")
```

### 环境变量映射

所有字段自动映射到环境变量：

```bash
# .env
APP_NAME="My Service"
MAX_RETRIES=3
CACHE_TTL=3600

# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb

# 缓存配置
CACHE_TYPE=redis
CACHE_URL=redis://localhost:6379/0
```

## 多实例配置

框架支持多实例配置，环境变量格式：`{PREFIX}_{INSTANCE}_{FIELD}`

### 数据库多实例

```bash
# 默认实例
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb
# 等同于
DATABASE_DEFAULT_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb

# 只读实例
DATABASE_READONLY_URL=postgresql+asyncpg://user:pass@replica:5432/mydb
DATABASE_READONLY_POOL_SIZE=20
```

### 缓存多实例

```bash
# 默认实例
CACHE_TYPE=redis
CACHE_URL=redis://localhost:6379/0

# 会话缓存实例
CACHE_SESSION_TYPE=redis
CACHE_SESSION_URL=redis://localhost:6379/2
CACHE_SESSION_MAX_SIZE=5000
```

### 在代码中获取多实例配置

```python
from aury.boot.application.config import BaseConfig

config = BaseConfig()

# 获取所有数据库实例配置
db_instances = config.get_database_instances()
# 返回: {"default": DatabaseInstanceConfig(...), "readonly": DatabaseInstanceConfig(...)}

# 获取所有缓存实例配置
cache_instances = config.get_cache_instances()
# 返回: {"default": CacheInstanceConfig(...), "session": CacheInstanceConfig(...)}

# 支持的多实例类型：
# - get_database_instances()
# - get_cache_instances()
# - get_storage_instances()
# - get_channel_instances()
# - get_mq_instances()
# - get_event_instances()
```

## 分层配置

### 组织配置文件

```python
# config.py
from aury.boot.application.config import BaseConfig
from pydantic import Field

# ========== 应用配置 ==========
class ApplicationSettings(BaseModel):
    """应用级别配置"""
    name: str = Field(default="My Service")
    version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

# ========== 业务配置 ==========
class BusinessSettings(BaseModel):
    """业务级别配置"""
    max_retries: int = Field(default=3)
    timeout: int = Field(default=30)
    cache_ttl: int = Field(default=3600)

# ========== 集成配置 ==========
class AppConfig(BaseConfig):
    """总配置"""
    
    # 应用设置
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    
    # 业务设置
    business: BusinessSettings = Field(default_factory=BusinessSettings)
    
    class Config:
        env_nested_delimiter = "__"  # 支持 APP__NAME 这样的嵌套环境变量
```

### 在代码中使用

```python
from config import AppConfig

config = AppConfig()

# 访问应用配置
app_name = config.app.name

# 访问业务配置
max_retries = config.business.max_retries

# 访问框架配置
database_url = config.database.url
```

## 环境特定配置

### 开发/生产配置切换

```python
# config.py
import os
from aury.boot.application.config import BaseConfig
from pydantic import Field

class AppConfig(BaseConfig):
    """应用配置"""
    
    # 检测环境
    environment: str = Field(default="development")
    
    # 根据环境调整配置
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"

# 在 main.py 中
config = AppConfig()

if config.is_development:
    # 开发特定配置
    pass
else:
    # 生产特定配置
    pass
```

### 环境变量文件

```bash
# .env.development
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dev_db
LOG_LEVEL=DEBUG
DEBUG=true

# .env.production
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/prod_db
LOG_LEVEL=INFO
DEBUG=false
```

## 验证配置

### 自定义验证器

```python
from pydantic import BaseModel, field_validator, Field

class AppConfig(BaseConfig):
    """应用配置"""
    
    max_retries: int = Field(ge=1, le=10, description="重试次数（1-10）")
    cache_ttl: int = Field(gt=0, description="缓存过期时间（>0）")
    
    @field_validator('cache_ttl')
    @classmethod
    def validate_cache_ttl(cls, v):
        if v < 60:
            raise ValueError("缓存过期时间不能少于 60 秒")
        return v
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql:', 'mysql:', 'sqlite:')):
            raise ValueError("数据库 URL 格式不支持")
        return v
```

## 配置加载优先级

从高到低：

1. 代码中显式传入的值
2. 环境变量
3. .env 文件
4. 字段默认值

```python
# 优先级演示
class AppConfig(BaseConfig):
    host: str = Field(default="127.0.0.1")  # 3. 默认值

# .env 文件中
# HOST=0.0.0.0  # 2. 环境变量

# 代码中
config = AppConfig(host="0.0.0.0")  # 1. 显式传入

# 最终：config.host = "0.0.0.0"（代码中的值）
```

## 配置文件加载

### 手动指定 .env 文件

```python
from dotenv import load_dotenv
from config import AppConfig

# 加载特定的 .env 文件
load_dotenv(".env.production")

config = AppConfig()
```

### 基于环境选择 .env 文件

```python
import os
from dotenv import load_dotenv
from config import AppConfig

env = os.getenv("ENVIRONMENT", "development")
env_file = f".env.{env}"

if os.path.exists(env_file):
    load_dotenv(env_file)

config = AppConfig()
```

## 敏感信息处理

### 避免泄露敏感信息

```python
class AppConfig(BaseConfig):
    """应用配置"""
    
    database_url: str = Field(description="数据库连接字符串")
    api_key: str = Field(description="API 密钥")
    secret_key: str = Field(description="应用密钥")
    
    def __str__(self):
        # 不要在字符串表示中暴露敏感信息
        return f"AppConfig(database=***,api_key=***,secret_key=***)"
    
    def model_dump(self):
        # 不要导出敏感信息
        data = super().model_dump()
        data["database_url"] = "***"
        data["api_key"] = "***"
        data["secret_key"] = "***"
        return data
```

### 从环境变量读取敏感信息

```bash
# 不要在 .env 中硬编码敏感信息！
# 而是从系统环境变量中读取

# 容器/CI 系统中设置
export DATABASE_PASSWORD="secure_password"
export API_KEY="secret_key"
```

## 动态配置

### 运行时更新配置

```python
from typing import Any

class AppConfig(BaseConfig):
    """应用配置"""
    
    cache_ttl: int = Field(default=3600)
    debug: bool = Field(default=False)
    
    def set_debug(self, enabled: bool):
        """设置调试模式"""
        self.debug = enabled
    
    def set_cache_ttl(self, ttl: int):
        """设置缓存过期时间"""
        if ttl < 60:
            raise ValueError("最小 60 秒")
        self.cache_ttl = ttl
```

### 配置重新加载

```python
import signal
from config import AppConfig

config = AppConfig()

def reload_config(signum, frame):
    """处理 SIGHUP 信号，重新加载配置"""
    global config
    config = AppConfig()
    print("配置已重新加载")

signal.signal(signal.SIGHUP, reload_config)
```

## 配置文档

### 自动生成配置文档

```python
from config import AppConfig
import json

# 生成 JSON Schema
schema = AppConfig.model_json_schema()
print(json.dumps(schema, indent=2, ensure_ascii=False))

# 生成 Markdown 文档
def generate_config_docs(config_class):
    schema = config_class.model_json_schema()
    for field, details in schema["properties"].items():
        print(f"- `{field}` ({details.get('type', 'string')})")
        print(f"  {details.get('description', 'No description')}")

generate_config_docs(AppConfig)
```

## 常见问题

### Q: 如何处理必需的配置？

A: 不设置默认值，Pydantic 会自动验证必需字段。

```python
class AppConfig(BaseConfig):
    database_url: str  # 必需，没有默认值
    # 对应的环境变量必须设置
```

### Q: 如何处理列表/字典类型的环境变量？

A: 使用 JSON 格式。

```bash
# .env
RPC_SERVICES='{"user-service": "http://localhost:8001", "order-service": "http://localhost:8002"}'
ALLOWED_HOSTS='["localhost", "127.0.0.1"]'
```

```python
class AppConfig(BaseConfig):
    rpc_services: dict = Field(default_factory=dict)
    allowed_hosts: list = Field(default_factory=list)
```

### Q: 如何测试配置？

A: 使用临时 .env 文件或环境变量。

```python
import pytest
from dotenv import load_dotenv
from config import AppConfig

@pytest.fixture
def test_config(tmp_path):
    env_file = tmp_path / ".env.test"
    env_file.write_text("DATABASE_URL=sqlite:///test.db\n")
    load_dotenv(env_file)
    return AppConfig()
```

## 下一步

- 查看 [06-di-container-complete.md](./06-di-container-complete.md) 了解依赖注入
- 查看 [04-project-structure.md](./04-project-structure.md) 了解项目组织


