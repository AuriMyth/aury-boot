"""AuriMyth Foundation Kit - 核心基础架构工具包。

提供数据库、缓存、认证等核心基础设施功能。

模块结构：
- common: 最基础层（异常基类、日志系统、国际化）
- domain: 领域层（业务模型、仓储接口、服务基类、分页、事务管理）
- infrastructure: 基础设施层（外部依赖的实现：数据库、缓存、存储、调度器等）
- application: 应用层（配置管理、RPC通信、依赖注入、事务管理、事件系统、迁移管理、API接口）
- toolkit: 工具包（通用工具函数）
- testing: 测试框架（测试基类、测试客户端、数据工厂）
"""

# Common 层（最基础层）
# 领域层
# 基础设施层
# 应用层（包含 interfaces）
# 工具包
# 测试框架
from . import application, common, domain, infrastructure, testing, toolkit

__version__ = "0.1.0"
__all__ = [
    "application",
    "common",
    "domain",
    "infrastructure",
    "testing",
    "toolkit",
]
