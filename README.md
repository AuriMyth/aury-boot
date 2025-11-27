# AuriMyth Foundation Kit

这是AuriMyth项目的核心基础架构工具包，提供所有微服务共用的基础设施组件。

## 功能模块

- **core**: 核心功能（数据库、缓存、任务调度等）
- **utils**: 工具函数（日志、安全、HTTP客户端等）
- **models**: 共享数据模型
- **repositories**: 基础仓储模式
- **services**: 基础服务类
- **adapters**: 第三方服务适配器
- **rpc**: RPC通信框架
- **errors**: 错误处理

## 使用方式

在AuriMyth工作区内的其他包中，可以直接导入：

```python
from aurimyth.foundation_kit.core.database import DatabaseManager
from aurimyth.foundation_kit.utils.logging import logger
```

## 开发指南

修改此包后，所有依赖它的服务都会自动使用最新版本，无需重新安装。




