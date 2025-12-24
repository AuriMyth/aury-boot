# {project_name} 开发指南

本文档基于 [Aury Boot](https://github.com/AuriMyth/aury-boot) 框架。

CLI 命令参考请查看 [CLI.md](../CLI.md)。

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
