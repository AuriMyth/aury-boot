"""通用工具集 - 面向对象设计。

所有工具都采用面向对象设计，提供清晰的接口和职责分离。
"""

# JWT工具
from .jwt import (
    AccessTokenPayload,
    JWTManager,
    RefreshTokenPayload,
    TokenPayload,
    TokenType,
    create_refresh_token,
    create_session_token,
    create_token,
    verify_token,
)

# 安全工具
from .security import (
    PasswordPolicy,
    PasswordStrength,
    SecurityManager,
    generate_random_password,
    generate_secure_token,
    hash_secret,
    validate_password_strength,
    verify_secret,
)

# 日志工具
from .logging import log_request, logger

# Repository基类（从repositories导入）
from aurimyth.foundation_kit.repositories.base import BaseRepository, IRepository, SimpleRepository

# HTTP客户端
from .http_client import HttpClient

# Chat客户端
from .chat import ChatClient

# 事务管理
from .transaction import (
    TransactionManager,
    transactional,
    transactional_context,
)

# Service基类（从services导入）
from aurimyth.foundation_kit.services.base import BaseService

# 依赖注入容器
from .container import Container, Lifetime, Scope, ServiceDescriptor

# 事件系统
from .events import (
    Event,
    EventBus,
    EventMiddleware,
    LoggingMiddleware,
    UserCreatedEvent,
    UserDeletedEvent,
    UserUpdatedEvent,
)

__all__ = [
    # JWT
    "JWTManager",
    "TokenType",
    "TokenPayload",
    "AccessTokenPayload",
    "RefreshTokenPayload",
    "create_token",
    "verify_token",
    "create_session_token",
    "create_refresh_token",
    # 安全
    "SecurityManager",
    "PasswordPolicy",
    "PasswordStrength",
    "hash_secret",
    "verify_secret",
    "validate_password_strength",
    "generate_secure_token",
    "generate_random_password",
    # 日志
    "logger",
    "log_request",
    # Repository
    "IRepository",
    "BaseRepository",
    "SimpleRepository",
    # HTTP
    "HttpClient",
    # Chat
    "ChatClient",
    # 事务
    "transactional",
    "transactional_context",
    "TransactionManager",
    # Service
    "BaseService",
    # 依赖注入
    "Container",
    "Scope",
    "Lifetime",
    "ServiceDescriptor",
    # 事件
    "Event",
    "EventBus",
    "EventMiddleware",
    "LoggingMiddleware",
    "UserCreatedEvent",
    "UserUpdatedEvent",
    "UserDeletedEvent",
]



