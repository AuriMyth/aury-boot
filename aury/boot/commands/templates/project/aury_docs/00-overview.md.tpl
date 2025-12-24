# {project_name} 开发指南

本文档基于 [Aury Boot](https://github.com/AuriMyth/aury-boot) 框架。

CLI 命令参考请查看 [99-cli.md](./99-cli.md)。

---

## 目录结构

```
{project_name}/
├── {package_name}/              # 代码包（默认 app，可通过 aury init <pkg> 自定义）
│   ├── models/       # SQLAlchemy ORM 模型
│   ├── repositories/ # 数据访问层
│   ├── services/     # 业务逻辑层
│   ├── schemas/      # Pydantic 请求/响应模型
│   ├── api/          # FastAPI 路由
│   ├── exceptions/   # 业务异常
│   ├── tasks/        # 异步任务（Dramatiq）
│   └── schedules/    # 定时任务（Scheduler）
├── tests/            # 测试
├── migrations/       # 数据库迁移
└── main.py           # 应用入口
```

---

## 最佳实践

1. **分层架构**：API → Service → Repository → Model
2. **事务管理**：在 Service 层使用 `@transactional`，只读操作可不加
3. **错误处理**：使用框架异常类，全局异常处理器统一处理
4. **配置管理**：使用 `.env` 文件，不提交到版本库
5. **日志记录**：使用框架 logger，支持结构化日志和链路追踪
6. **多实例配置**：环境变量格式 `{{PREFIX}}_{{INSTANCE}}_{{FIELD}}`

---

## 文档索引

### CRUD / 数据库
- [01-model.md](./01-model.md) - Model 定义
- [02-repository.md](./02-repository.md) - Repository 使用
- [03-service.md](./03-service.md) - Service 与事务
- [04-schema.md](./04-schema.md) - Pydantic Schema
- [05-api.md](./05-api.md) - API 路由
- [06-exception.md](./06-exception.md) - 异常处理

### 基础设施
- [07-cache.md](./07-cache.md) - 缓存
- [08-scheduler.md](./08-scheduler.md) - 定时任务
- [09-tasks.md](./09-tasks.md) - 异步任务
- [10-storage.md](./10-storage.md) - 对象存储
- [11-logging.md](./11-logging.md) - 日志
- [12-admin.md](./12-admin.md) - 管理后台
- [13-channel.md](./13-channel.md) - 流式通道（SSE）
- [14-mq.md](./14-mq.md) - 消息队列
- [15-events.md](./15-events.md) - 事件总线
