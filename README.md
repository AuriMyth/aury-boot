# AuriMyth Foundation Kit

这是AuriMyth项目的核心基础架构工具包，提供所有微服务共用的基础设施组件。

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
from aurimyth.foundation_kit.i18n import Translator, translate, set_locale

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
from aurimyth.foundation_kit.testing import TestCase, TestClient, Factory

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
from aurimyth.foundation_kit.migrations import MigrationManager

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
aurimyth-migrate make -m "add user table"

# 执行迁移
aurimyth-migrate up

# 回滚迁移
aurimyth-migrate down

# 查看状态
aurimyth-migrate status

# 显示迁移历史
aurimyth-migrate show
```

## 使用方式

在AuriMyth工作区内的其他包中，可以直接导入：

```python
from aurimyth.foundation_kit.infrastructure.database import DatabaseManager
from aurimyth.foundation_kit.infrastructure.logging import logger
from aurimyth.foundation_kit.core import BaseModel, BaseRepository, BaseService
from aurimyth.foundation_kit.interfaces import BaseRequest, BaseResponse
from aurimyth.foundation_kit.application.rpc import RPCClient
```

## 开发指南

修改此包后，所有依赖它的服务都会自动使用最新版本，无需重新安装。

## 安装

```bash
pip install aurimyth-foundation-kit
```

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/aurimyth/foundation-kit.git
cd foundation-kit

# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black aurimyth/
pylint aurimyth/
mypy aurimyth/
```




