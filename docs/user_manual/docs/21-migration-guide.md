# 20. 数据库迁移指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 20 章的快速开始。

## Kit 提供的迁移命令

Aury Boot 提供了完整的迁移管理命令，类似 Django 的 `migrate` 命令：

```bash
# 生成迁移文件
aury migrate make -m "Add users table"

# 执行迁移
aury migrate up

# 回滚迁移
aury migrate down -1

# 查看迁移状态
aury migrate status

# 显示所有迁移
aury migrate show

# 检查迁移问题
aury migrate check
```

## 自动迁移（推荐）

Kit 提供了 `MigrationComponent`，可以在应用启动时自动执行迁移：

```python
from aury.boot.application.app.base import FoundationApp
from aury.boot.application.config import BaseConfig
from aury.boot.application.app.components import MigrationComponent

class AppConfig(BaseConfig):
    pass

app = FoundationApp(
    title="My Service",
    version="0.1.0",
    config=AppConfig()
)

# MigrationComponent 会在应用启动时自动执行迁移
class MyApp(FoundationApp):
    items = [
        # ... 其他组件 ...
        MigrationComponent,  # 应用启动时自动执行迁移
    ]
```

应用启动时输出：
```
🔄 检查数据库迁移...
📊 数据库迁移状态：
   已执行: 5 个迁移
   待执行: 2 个迁移
⏳ 执行数据库迁移...
✅ 数据库迁移完成
```

### 禁用自动迁移

如果需要手动控制迁移，可以禁用自动迁移：

```python
class MyApp(FoundationApp):
    items = [
        # 不包含 MigrationComponent
        DatabaseComponent,
        CacheComponent,
        # ...
    ]

# 然后手动执行
aury migrate up
```

## 初始化项目

### 步骤 1：初始化 Alembic

```bash
# 初始化 Alembic（异步支持）
alembic init -t async alembic
```

这会创建 `alembic/` 目录结构：
```
alembic/
├── versions/           # 迁移文件目录
├── env.py             # 环境配置
├── script.py.mako     # 迁移模板
└── alembic.ini        # Alembic 配置
```

### 步骤 2：配置 Alembic

编辑 `alembic/env.py`，配置数据库连接和 SQLAlchemy 元数据：

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import asyncio
from app.config import Config
from app.models import Base  # 你的 Base 类

config = Config()
sqlalchemy_url = config.database.url

def run_migrations_online():
    """在与数据库连接的情况下执行迁移。"""
    
    connectable = create_async_engine(sqlalchemy_url, echo=False)

    async with connectable.begin() as connection:
        await connection.run_sync(run_migrations)

    await connectable.dispose()

def run_migrations_offline():
    """在离线模式下执行迁移。"""
    context.configure(
        url=sqlalchemy_url,
        version_table_schema=target_metadata.schema,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

## 常见工作流

### 1. 自动生成迁移（推荐）

#### 步骤 1：修改模型

```python
# models/user.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from aury.boot.domain.models.base import Base, GUID

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(GUID, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    # Base 自动包含：created_at, updated_at
```

#### 步骤 2：检查变更（干运行）

```bash
# 只检测变更，不生成文件
aury migrate make -m "Add users table" --dry-run
```

输出：
```
📝 检测到 3 个变更:
  - create_table: users
  - create_unique_constraint: users.username
  - create_unique_constraint: users.email
```

#### 步骤 3：生成迁移文件

```bash
# 自动生成迁移脚本
aury migrate make -m "Add users table"

# 输出: ✅ 迁移文件已生成: alembic/versions/2024_01_01_120000_add_users_table.py
```

生成的迁移文件自动包含所有必要的 SQL 操作。

#### 步骤 4：执行迁移

```bash
# 执行到最新版本
aury migrate up

# 或指定版本
aury migrate up -r "2024_01_01_120000"
```

### 2. 查看迁移状态

```bash
# 查看当前状态
aury migrate status

# 输出:
# 📊 迁移状态:
#   当前版本: 2024_01_01_120000
#   最新版本: 2024_01_02_140000
#
# ⏳ 待执行迁移 (1):
#   - 2024_01_02_140000
```

### 3. 显示所有迁移

```bash
# 显示迁移列表
aury migrate show

# 输出表格显示所有迁移
```

### 4. 回滚迁移

```bash
# 回滚一个版本
aury migrate down -1

# 回滚到前一个版本
aury migrate down previous

# 回滚到指定版本
aury migrate down "2024_01_01_100000"

# 干运行（只显示会回滚的迁移，不实际执行）
aury migrate down -1 --dry-run
```

### 5. 检查迁移问题

```bash
# 检查迁移文件是否有问题
aury migrate check

# 输出:
# ✅ 迁移检查通过
#
# 📊 统计:
#   迁移总数: 5
#   Head 数量: 1
```

### 6. 查看迁移历史

```bash
# 显示迁移历史
aury migrate history

# 详细模式
aury migrate history --verbose
```

## 常见场景

### 添加新列

```bash
# 1. 修改模型
# class User(Base):
#     new_field: Mapped[str] = mapped_column(String(100), nullable=True)

# 2. 生成迁移
aury migrate make -m "Add new_field to users"

# 3. 执行迁移
aury migrate up
```

### 删除列

```bash
# 1. 从模型删除字段
# class User(Base):
#     # 删除 new_field

# 2. 生成迁移
aury migrate make -m "Remove new_field from users"

# 3. 执行迁移
aury migrate up
```

### 添加索引

```bash
# 1. 修改模型
# class User(Base):
#     email: Mapped[str] = mapped_column(String(100), index=True)

# 2. 生成迁移
aury migrate make -m "Add index on users.email"

# 3. 执行迁移
aury migrate up
```

### 添加关联字段

> **最佳实践**：不建议使用数据库外键，通过程序控制关系。

```bash
# 1. 修改模型（不使用 ForeignKey）
# import uuid
# class User(Base):
#     profile_id: Mapped[uuid.UUID | None] = mapped_column(index=True)

# 2. 生成迁移
aury migrate make -m "Add profile_id to users"

# 3. 执行迁移
aury migrate up
```

### 修改列类型

```bash
# 1. 修改模型
# class User(Base):
#     username: Mapped[str] = mapped_column(String(100))  # 从 50 改为 100

# 2. 生成迁移
aury migrate make -m "Increase username length"

# 3. 执行迁移
aury migrate up
```

## 环境变量配置

在 `.env` 中配置数据库 URL：

```bash
# 开发环境
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mydb_dev

# 测试环境
DATABASE_URL=postgresql+asyncpg://user:pass@testdb:5432/mydb_test

# 生产环境
DATABASE_URL=postgresql+asyncpg://user:pass@proddb:5432/mydb_prod
```

## 手动编写迁移

如果需要手动编写迁移（不自动生成）：

```bash
# 创建空迁移文件
aury migrate make -m "Custom migration" --no-autogenerate

# 编辑生成的文件：alembic/versions/xxx_custom_migration.py
```

编辑迁移文件：

```python
def upgrade():
    # 编写升级逻辑
    op.execute("CREATE INDEX idx_users_email ON users(email)")

def downgrade():
    # 编写回滚逻辑
    op.execute("DROP INDEX idx_users_email")
```

## 版本控制

### 最佳实践

1. ✅ **提交迁移文件到 Git**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration: add users table"
   ```

2. ✅ **命名迁移文件**
   - 使用有意义的名字：`add_users_table`、`add_index_on_email`
   - 避免使用：`fix_bug`、`temp_migration`

3. ✅ **团队协作**
   - 每个特性分支一个迁移
   - 使用 `aury migrate merge` 合并冲突的迁移
   - 定期合并迁移

4. ✅ **生产部署**
   ```bash
   # 部署前先在测试环境验证
   aury migrate status         # 查看待执行迁移
   aury migrate up --dry-run   # 检查会执行的迁移
   aury migrate up             # 执行迁移
   ```

## 常见问题

### Q: 如何查看待执行的 SQL？
```bash
# 检查状态
aury migrate status

# 干运行
aury migrate up --dry-run
```

### Q: 迁移失败了怎么办？
```bash
# 1. 查看当前状态
aury migrate status

# 2. 查看错误日志
# 3. 修复问题后重试
aury migrate up
```

### Q: 如何解决迁移冲突？
```bash
# 当有多个分支的迁移时，使用 merge 合并
aury migrate merge "abc123,def456" -m "merge branches"
```

### Q: 如何检查迁移的有效性？
```bash
# 检查迁移文件
aury migrate check

# 显示所有迁移
aury migrate show

# 显示历史
aury migrate history --verbose
```

---

**总结**：使用 `aury migrate make -m "description"` 自动生成迁移，Kit 会自动检测模型变更并生成必要的 SQL。无需手动编写 SQL，安全且高效！
