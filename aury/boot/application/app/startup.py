"""启动日志工具。

提供应用启动时的组件状态打印功能，包括 URL 脱敏。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from aury.boot.common.logging import logger


@dataclass
class ComponentStatus:
    """组件状态。"""

    name: str
    status: str  # "ok", "error", "disabled"
    backend: str | None = None
    url: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def mask_url(url: str | None) -> str:
    """URL 脱敏（隐藏密码和敏感信息）。

    Args:
        url: 原始 URL

    Returns:
        脱敏后的 URL
    """
    if not url:
        return "N/A"

    # 匹配常见 URL 格式中的密码部分
    # redis://:password@host:port/db
    # amqp://user:password@host:port/vhost
    # postgresql://user:password@host:port/db
    patterns = [
        # user:password@ 格式
        (r"(://[^:]+:)([^@]+)(@)", r"\1***\3"),
        # :password@ 格式 (无用户名)
        (r"(://:)([^@]+)(@)", r"\1***\3"),
    ]

    masked = url
    for pattern, replacement in patterns:
        masked = re.sub(pattern, replacement, masked)

    return masked


def print_startup_banner(
    app_name: str = "Aury Boot",
    version: str = "",
    components: list[ComponentStatus] | None = None,
) -> None:
    """打印启动横幅和组件状态。

    Args:
        app_name: 应用名称
        version: 版本号
        components: 组件状态列表
    """
    # 打印横幅
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║  {app_name:^58}  ║
║  {f'v{version}' if version else '':^58}  ║
╚══════════════════════════════════════════════════════════════╝
"""
    logger.info(banner)

    # 打印组件状态
    if components:
        logger.info("组件状态:")
        logger.info("-" * 60)

        for comp in components:
            status_icon = "✓" if comp.status == "ok" else "✗" if comp.status == "error" else "○"
            status_text = f"[{status_icon}] {comp.name}"

            if comp.backend:
                status_text += f" ({comp.backend})"

            if comp.url:
                status_text += f" -> {mask_url(comp.url)}"

            if comp.status == "error" and comp.details.get("error"):
                status_text += f" | Error: {comp.details['error']}"

            logger.info(f"  {status_text}")

        logger.info("-" * 60)


def collect_component_status() -> list[ComponentStatus]:
    """收集所有组件状态。

    Returns:
        组件状态列表
    """
    from aury.boot.infrastructure.cache import CacheManager
    from aury.boot.infrastructure.database import DatabaseManager
    from aury.boot.infrastructure.scheduler import SchedulerManager
    from aury.boot.infrastructure.storage import StorageManager

    # 延迟导入新模块（可能不存在）
    try:
        from aury.boot.infrastructure.clients.redis import RedisClient
    except ImportError:
        RedisClient = None

    try:
        from aury.boot.infrastructure.channel import ChannelManager
    except ImportError:
        ChannelManager = None

    try:
        from aury.boot.infrastructure.mq import MQManager
    except ImportError:
        MQManager = None

    try:
        from aury.boot.infrastructure.events import EventBusManager
    except ImportError:
        EventBusManager = None

    statuses = []

    # Database - 收集所有实例
    for name, instance in DatabaseManager._instances.items():
        if instance.is_initialized:
            url = str(instance._engine.url) if instance._engine else None
            statuses.append(
                ComponentStatus(
                    name="Database" if name == "default" else f"Database [{name}]",
                    status="ok",
                    backend="SQLAlchemy",
                    url=url,
                )
            )

    # Cache - 收集所有实例
    for name, instance in CacheManager._instances.items():
        if instance._backend:
            statuses.append(
                ComponentStatus(
                    name="Cache" if name == "default" else f"Cache [{name}]",
                    status="ok",
                    backend=instance.backend_type,
                    url=instance._config.get("CACHE_URL") if instance._config else None,
                )
            )

    # Storage - 收集所有实例
    for name, instance in StorageManager._instances.items():
        if instance._backend:
            backend_type = instance._config.backend.value if instance._config else "unknown"
            url = None
            if instance._config:
                if backend_type == "local":
                    url = instance._config.base_path
                elif instance._config.endpoint:
                    url = instance._config.endpoint
            statuses.append(
                ComponentStatus(
                    name="Storage" if name == "default" else f"Storage [{name}]",
                    status="ok",
                    backend=backend_type,
                    url=url,
                )
            )

    # Scheduler
    scheduler = SchedulerManager.get_instance()
    if scheduler._initialized:
        statuses.append(
            ComponentStatus(
                name="Scheduler",
                status="ok",
                backend="APScheduler",
            )
        )

    # Redis Clients
    if RedisClient:
        for name, instance in RedisClient._instances.items():
            if instance.is_initialized:
                statuses.append(
                    ComponentStatus(
                        name="Redis" if name == "default" else f"Redis [{name}]",
                        status="ok",
                        backend="redis",
                        url=instance._config.url if instance._config else None,
                    )
                )

    # Channel
    if ChannelManager:
        for name, instance in ChannelManager._instances.items():
            if instance.is_initialized:
                statuses.append(
                    ComponentStatus(
                        name="Channel" if name == "default" else f"Channel [{name}]",
                        status="ok",
                        backend=instance.backend_type,
                        url=getattr(instance._backend, "_url", None) if instance._backend else None,
                    )
                )

    # MQ
    if MQManager:
        for name, instance in MQManager._instances.items():
            if instance.is_initialized:
                statuses.append(
                    ComponentStatus(
                        name="MQ" if name == "default" else f"MQ [{name}]",
                        status="ok",
                        backend=instance.backend_type,
                        url=getattr(instance._backend, "_url", None) if instance._backend else None,
                    )
                )

    # Events
    if EventBusManager:
        for name, instance in EventBusManager._instances.items():
            if instance.is_initialized:
                statuses.append(
                    ComponentStatus(
                        name="Events" if name == "default" else f"Events [{name}]",
                        status="ok",
                        backend=instance.backend_type,
                        url=getattr(instance._backend, "_url", None) if instance._backend else None,
                    )
                )

    return statuses


__all__ = [
    "ComponentStatus",
    "collect_component_status",
    "mask_url",
    "print_startup_banner",
]
