# Aury Boot

基于 FastAPI 生态的企业级 API 开发框架，提供所有微服务共用的基础设施组件。

## 快速开始

```bash
# 1. 创建项目目录并初始化
mkdir my-service && cd my-service
uv init . --name my_service --no-package --python 3.13

# 2. 添加依赖
uv add "aury-boot[recommended,admin]"  # admin 可选，提供 SQLAdmin 管理后台

# 3. 初始化项目结构
aury init

# 4. 启动开发服务器
aury server dev
```

## 功能模块

- **core**: 核心功能（数据库、缓存、任务调度等）
- **utils**: 工具函数（日志、安全、HTTP客户端等）
- **models**: 共享数据模型和响应模型
- **repositories**: 基础仓储模式
- **services**: 基础服务类
- **adapters**: 第三方服务适配器
- **rpc**: RPC通信框架
- **exceptions**: 错误处理系统
- **i18n**: 国际化支持
- **testing**: 测试框架
- **migrations**: 数据库迁移工具

## 主要功能

### 1. 国际化支持 (i18n)

提供完整的多语言支持，包括文本翻译、日期/数字本地化等：

```python
from aury.boot.i18n import Translator, translate, set_locale

# 设置语言环境
set_locale("zh_CN")

# 使用翻译器
translator = Translator(locale="zh_CN")
message = translator.translate("user.created", name="张三")

# 使用简写函数
message = translate("user.created", name="张三")

# 装饰器方式
@_("user.title")
def get_user_title():
    return "User Title"  # 会被翻译
```

### 2. 测试框架

提供便捷的测试工具，包括测试基类、测试客户端、数据工厂等：

```python
from aury.boot.testing import TestCase, TestClient, Factory

class UserServiceTest(TestCase):
    """测试基类，自动处理数据库事务回滚"""
    
    async def setUp(self):
        """测试前准备"""
        self.client = TestClient(app)
        self.user_factory = Factory(User)
    
    async def test_create_user(self):
        """测试创建用户"""
        user = await self.user_factory.create(name="张三")
        response = await self.client.post("/users", json={"name": "张三"})
        assert response.status_code == 201
```

### 3. 数据库迁移工具

提供便捷的数据库迁移管理，类似 Django 的命令行接口：

```python
from aury.boot.migrations import MigrationManager

# 使用 Python API
migration_manager = MigrationManager()
await migration_manager.make_migrations(message="add user table")
await migration_manager.migrate_up()
await migration_manager.migrate_down(version="previous")
status = await migration_manager.status()
```

命令行工具：

```bash
# 生成迁移文件
aury migrate make -m "add user table"

# 执行迁移
aury migrate up

# 回滚迁移
aury migrate down

# 查看状态
aury migrate status

# 显示迁移历史
aury migrate show
```

### 4. 代码生成器

快速生成标准的 CRUD 代码（模型、仓储、服务、API 路由）：

```bash
# 生成完整 CRUD（Model + Repository + Service + API）
aury generate crud user

# 单独生成各层代码
aury generate model user      # SQLAlchemy 模型
aury generate repo user       # Repository 仓储层
aury generate service user    # Service 服务层
aury generate api user        # API 路由

# 交互式生成（推荐）：逐步选择字段、类型、验证规则
aury generate crud user -i
aury generate model user -i

# 指定字段（非交互式）
aury generate model user --fields "name:str,email:str,age:int"
```

**交互式模式 (`-i`)** 会引导你：
- 添加字段名称和类型
- 设置字段约束（唯一、可空、默认值等）
- 配置关系字段（外键、多对多等）
- 自动插入 API 路由到 `api/__init__.py`

生成的代码遵循项目架构模式，开箱即用。

## 使用方式

在AUM工作区内的其他包中，可以直接导入：

```python
from aury.boot.infrastructure.database import DatabaseManager
from aury.boot.infrastructure.logging import logger
from aury.boot.core import BaseModel, BaseRepository, BaseService
from aury.boot.interfaces import BaseRequest, BaseResponse
from aury.boot.application.rpc import RPCClient
```

## 开发指南

修改此包后，所有依赖它的服务都会自动使用最新版本，无需重新安装。

## 安装

```bash
# 推荐（PostgreSQL + Redis + 任务队列 + 调度器）
uv add "aury-boot[recommended]"

# 或按需组合
uv add "aury-boot[postgres,redis]"

# 全部依赖
uv add "aury-boot[all]"
```

### 可选依赖

| 名称 | 说明 |
|------|------|
| `postgres` | PostgreSQL 数据库 |
| `mysql` | MySQL 数据库 |
| `sqlite` | SQLite 数据库 |
| `redis` | Redis 缓存 |
| `s3` | S3 对象存储 |
| `tasks` | 任务队列 |
| `rabbitmq` | RabbitMQ 支持 |
| `scheduler` | 定时调度 |
| `recommended` | 推荐组合 |
| `all` | 全部依赖 |

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/AuriMyth/aury-boot.git
cd aury-boot

# 安装依赖
uv sync --group dev

# 运行测试
pytest

# 代码检查
ruff check .
mypy aury/
```




