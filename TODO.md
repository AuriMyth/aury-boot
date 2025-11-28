# Core 层优化 TODO

> **技术栈要求**：
> - Python 3.13 特性（`datetime.UTC`、现代类型提示、`match-case` 等）
> - SQLAlchemy 2.0+（`DeclarativeBase`、异步支持、类型提示）
> - Pydantic 2.5+（数据验证、序列化）
> - 优先使用成熟开源库，避免重复造轮子

## 🔴 高优先级（核心修复）

- [x] 1. 修复时间戳字段问题
  - ✅ Python 3.13: `datetime.UTC`（替代 `timezone.utc`）
  - ✅ SQLAlchemy 2.0: `DeclarativeBase`、`DateTime(timezone=True)`
  - ✅ `server_default=func.now()`（数据库端） + `default` + `onupdate`（Python 端）

- [x] 2. 软删除机制扩展
  - ✅ `SoftDeleteModel` + `deleted_at` 字段
  - ✅ Repository: `hard_delete()` / `soft_delete()` 方法
  - ✅ 自动过滤已删除记录

- [x] 3. 主键类型扩展
  - ✅ `UUIDModel` + `UUIDSoftDeleteModel` 基类
  - ✅ 跨数据库 `GUID` 类型装饰器（PostgreSQL 原生 UUID，其他数据库 CHAR(36)）

- [x] 4. 版本控制（乐观锁）
  - ✅ `VersionedModel` + `VersionConflictError` 异常
  - ✅ Repository `update()` 自动版本检查和自增

## 🟡 中优先级（Repository 增强）

- [ ] 5. 查询构建器增强
  - SQLAlchemy 2.0: `select()`、`where()`、链式查询
  - 操作符支持：`__gt`、`__lt`、`__in`、`__like`、`__isnull`
  - 复杂条件：`and_()`、`or_()`、`not_()`
  - 关系查询：`joinedload()`、`selectinload()`

- [ ] 6. 批量操作优化
  - SQLAlchemy 2.0: `bulk_insert_mappings()`、`bulk_update_mappings()`
  - 批量删除：`bulk_delete()`
  - `bulk_upsert()`（使用 `ON CONFLICT` 或数据库特定语法）

- [ ] 7. 分页和排序标准化
  - Pydantic 2.5: `PaginationParams`、`SortParams`、`PaginationResult[T]`
  - 参考 FastAPI Pagination 最佳实践
  - 支持游标分页（cursor-based pagination）

- [ ] 8. 事务边界检查
  - Python 3.13: 装饰器 + 类型提示
  - `@requires_transaction` 装饰器
  - 抛出 `TransactionRequiredError` 异常

- [ ] 9. QueryInterceptor 接口
  - SQLAlchemy 2.0 Events: `before_cursor_execute`、`after_cursor_execute`
  - 查询拦截器注册机制
  - `before_query()` / `after_query()` 钩子

- [ ] 10. 类型安全增强
  - Python 3.13: `TypedDict`、泛型类型提示
  - 类型安全查询方法（IDE 自动补全）
  - `typing_extensions`（如需要）

- [ ] 11. 查询结果缓存
  - 集成现有 `CacheManager`（Redis/Memory）
  - `@cache_query` 装饰器
  - 缓存键生成策略、TTL 支持

- [ ] 12. 查询性能监控
  - 集成 Loguru（现有日志系统）
  - 慢查询日志（可配置阈值）
  - SQLAlchemy `explain()` 支持

## 🟡 中优先级（Service 增强）

- [ ] 13. Repository 自动注入
  - 集成现有 `Container`（DI 系统）
  - `@inject_repository` 装饰器或属性装饰器
  - 支持多个 Repository 的自动注入

- [ ] 14. 事务管理增强
  - SQLAlchemy 2.0: 事务传播级别、只读事务
  - `@readonly` 装饰器
  - 事务超时设置

- [ ] 15. 服务组合模式
  - `CompositeService` 基类
  - 服务间依赖声明
  - 服务编排能力（类似 Saga 模式）

- [ ] 16. 业务事件发布
  - 集成现有 `EventBus`（事件系统）
  - `@publish_event` 装饰器
  - 事务后事件（事务提交后发布）

- [ ] 17. 验证装饰器
  - Pydantic 2.5: `@validate` 装饰器
  - 方法级别参数验证、返回值验证
  - 自动错误转换

- [ ] 18. 服务层缓存
  - 集成现有 `CacheManager`
  - `@cache_result` 装饰器
  - 缓存键生成策略、失效策略（事件/TTL）

- [ ] 19. 错误处理标准化
  - `ServiceException` 基类
  - 集成 `interfaces.errors`（现有错误系统）
  - 业务异常自动转换

- [ ] 20. 性能监控装饰器
  - 集成 Loguru（现有日志系统）
  - `@monitor` 装饰器（执行时间、调用次数）
  - 支持 Prometheus 格式导出（可选）

## 🟡 中优先级（配置管理）

- [ ] 21. 多环境配置管理
  - `pydantic-settings` 2.11+（现有配置系统）
  - `ruamel.yaml` 或 `pyyaml`（YAML 解析）
  - `ConfigManager` 类（配置合并、环境变量优先级）

- [ ] 22. 密钥管理基础
  - `SecretManager` 接口（抽象基类）
  - `EnvironmentSecretManager`（环境变量）
  - `FileSecretManager`（本地文件，可选加密）
  - 高级集成（Vault、AWS Secrets Manager）作为插件

## 🔵 低优先级（测试工具）

- [ ] 23. MockRepository 和 InMemoryRepository
  - 集成现有测试框架（`pytest`、`pytest-asyncio`）
  - `MockRepository` 基类（用于单元测试）
  - `InMemoryRepository` 实现（内存存储）

- [ ] 24. Fixtures 支持
  - `pydantic`（数据验证）
  - `ruamel.yaml` 或 `pyyaml`（YAML 支持）
  - `FixturesLoader` 类（JSON/YAML 格式）
  - `TestCase` 集成（自动加载）

---

**进度**: 4/24 已完成 (16.7%)

**技术栈**:
- Python 3.13
- SQLAlchemy 2.0+
- Pydantic 2.5+
- Loguru（日志）
- pytest（测试）
- ruamel.yaml / pyyaml（YAML）

