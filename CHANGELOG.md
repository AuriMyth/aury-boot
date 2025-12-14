# Changelog

本文件记录 AuriMyth Foundation Kit 的重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/)，版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Added
- **命名多实例支持**：所有 Manager 类（`DatabaseManager`、`CacheManager`、`StorageManager`、`SchedulerManager`、`TaskManager`）现在支持命名多实例模式
  ```python
  # 默认实例（向后兼容）
  db = DatabaseManager.get_instance()
  
  # 命名实例
  primary = DatabaseManager.get_instance("primary")
  replica = DatabaseManager.get_instance("replica")
  
  source = StorageManager.get_instance("source")
  target = StorageManager.get_instance("target")
  ```
- 所有 Manager 新增 `reset_instance(name: str | None = None)` 方法，用于测试时重置实例

### Changed
- **Storage 模块重构**：移除内置存储实现，改为依赖 `aurimyth-storage-sdk`
  - 安装方式：`pip install "aurimyth-storage-sdk[aws]"` 或 `uv add "aurimyth-storage-sdk[aws]"`
  - `StorageManager` 现在委托给 SDK 的 `IStorage` 实现
  - 移除了 `s3.py`、`sts.py`、`sts_providers/` 等文件
  - STS 临时凭证功能现在通过 `aurimyth_storage_sdk.sts` 模块提供
- Manager 单例模式从类变量 `_instance` 改为 `_instances: dict[str, Manager]`
- `DatabaseManager.configure()` 从类方法改为实例方法

### Removed
- 移除内置的 S3/COS/OSS 存储实现（由 `aurimyth-storage-sdk` 替代）
- 移除内置的 STS 临时凭证提供者（由 `aurimyth-storage-sdk` 替代）

### Fixed
- 修复项目模板中的 f-string 和 JSON 字典转义问题

---

## [0.0.1] - 2024-12-xx

### Added
- 初始版本发布
- **核心框架**
  - `FoundationApp`：基于 FastAPI 的应用框架
  - `Component` 系统：组件生命周期管理
  - `BaseConfig`：Pydantic 配置管理
- **Domain 层**
  - `BaseRepository`：通用仓储模式实现
  - 预定义模型基类：`Model`、`UUIDModel`、`UUIDAuditableStateModel` 等
  - `@transactional` 装饰器：声明式事务管理
  - `QueryBuilder`：链式查询构建器
- **Infrastructure 层**
  - `DatabaseManager`：异步数据库连接管理
  - `CacheManager`：缓存管理（支持 Redis/Memory）
  - `TaskManager`：异步任务队列（Dramatiq）
  - `SchedulerManager`：定时任务调度（APScheduler）
  - `EventBus`：事件总线
- **Application 层**
  - 内置组件：Database、Cache、Storage、Task、Scheduler、Migration、AdminConsole
  - 标准响应模型：`BaseResponse`、`PaginationResponse`
  - 统一异常处理
- **CLI 工具**
  - `aum init`：项目脚手架
  - `aum generate crud`：CRUD 代码生成
  - `aum server dev/prod`：服务器管理
  - `aum migrate`：数据库迁移
- **文档**
  - 完整的用户手册
  - 项目模板（DEVELOPMENT.md、CLI.md）
