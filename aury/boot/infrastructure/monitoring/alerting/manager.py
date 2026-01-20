"""告警管理器。

核心告警处理逻辑，包括：
- 规则匹配
- 事件聚合
- 通知发送
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

from .aggregator import AlertAggregator
from .events import AlertEvent, AlertEventType, AlertNotification, AlertSeverity
from .rules import AlertRule, load_rules_from_dict

if TYPE_CHECKING:
    from .notifiers.base import AlertNotifier


class AlertManager:
    """告警管理器。
    
    负责处理告警事件、匹配规则、聚合事件、发送通知。
    
    使用方式：
        # 初始化（通常在应用启动时）
        alert_manager = AlertManager.get_instance()
        await alert_manager.initialize(config)
        
        # 发送告警事件
        await alert_manager.emit(AlertEvent(...))
        
        # 或使用便捷函数
        await emit_alert(AlertEventType.SLOW_REQUEST, "慢请求", duration=1.5)
    """
    
    _instance: "AlertManager | None" = None
    _notifier_classes: dict[str, type["AlertNotifier"]] = {}
    
    def __init__(self) -> None:
        """初始化告警管理器。"""
        self._enabled = False
        self._service_name = ""
        self._rules: list[AlertRule] = []
        self._notifiers: dict[str, "AlertNotifier"] = {}
        self._aggregators: dict[str, AlertAggregator] = {}  # 每个规则一个聚合器
        self._defaults: dict[str, Any] = {}
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> "AlertManager":
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def register_notifier_class(cls, name: str, notifier_cls: type["AlertNotifier"]) -> None:
        """注册通知器类型。
        
        Args:
            name: 类型名称（如 "feishu", "webhook"）
            notifier_cls: 通知器类
        """
        cls._notifier_classes[name] = notifier_cls
    
    async def initialize(
        self,
        *,
        enabled: bool = True,
        service_name: str = "",
        rules_file: str | Path | None = None,
        defaults: dict[str, Any] | None = None,
        notifiers: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """初始化告警管理器。
        
        Args:
            enabled: 是否启用告警
            service_name: 服务名称
            rules_file: 规则文件路径（YAML）
            defaults: 默认配置
            notifiers: 通知器配置（从 config.alert.get_notifiers() 获取）
        """
        self._enabled = enabled
        self._service_name = service_name
        self._defaults = defaults or {}
        
        if not enabled:
            logger.info("告警系统已禁用")
            return
        
        # 注册内置通知器类型
        self._register_builtin_notifiers()
        
        # 从配置加载内置通知器
        if notifiers:
            self._load_notifiers_from_config(notifiers)
        
        # 加载规则
        if rules_file:
            await self._load_rules_from_file(rules_file)
        
        # 如果没有规则，创建默认规则
        if not self._rules:
            self._create_default_rules()
        
        # 为每个规则创建聚合器
        for rule in self._rules:
            self._aggregators[rule.name] = AlertAggregator(
                window_seconds=rule.aggregate_window,
                threshold=rule.aggregate_threshold,
                suppress_seconds=rule.suppress_seconds,
            )
        
        self._initialized = True
        logger.info(
            f"告警系统已初始化: {len(self._rules)} 条规则, "
            f"{len(self._notifiers)} 个通知器"
        )
    
    def _register_builtin_notifiers(self) -> None:
        """注册内置通知器类型。"""
        from .notifiers.feishu import FeishuNotifier
        from .notifiers.webhook import WebhookNotifier
        
        self.register_notifier_class("feishu", FeishuNotifier)
        self.register_notifier_class("webhook", WebhookNotifier)
    
    def _load_notifiers_from_config(
        self,
        notifiers: dict[str, dict[str, Any]],
    ) -> None:
        """从配置加载通知器。
        
        Args:
            notifiers: 通知器配置（从 config.alert.get_notifiers() 获取）
        """
        for name, config in notifiers.items():
            # type 字段决定通知器类型，默认用实例名
            notifier_type = config.pop("type", name)
            notifier_cls = self._notifier_classes.get(notifier_type)
            
            if not notifier_cls:
                logger.warning(f"未知的通知器类型: {notifier_type}，跳过 {name}")
                continue
            
            try:
                notifier = notifier_cls.from_config(config)
                self._notifiers[name] = notifier
                logger.debug(f"已加载通知器: {name} ({notifier_type})")
            except Exception as e:
                logger.error(f"加载通知器 {name} 失败: {e}")
        
        # 如果有 notifier，将第一个设为 default
        if self._notifiers and "default" not in self._notifiers:
            first_name = next(iter(self._notifiers))
            self._notifiers["default"] = self._notifiers[first_name]
    
    async def _load_rules_from_file(self, rules_file: str | Path) -> None:
        """从 YAML 文件加载规则。"""
        rules_path = Path(rules_file)
        if not rules_path.exists():
            logger.warning(f"规则文件不存在: {rules_path}")
            return
        
        try:
            import yaml
            with open(rules_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if data:
                defaults, rules = load_rules_from_dict(data)
                self._defaults.update(defaults)
                self._rules.extend(rules)
                logger.info(f"从 {rules_path} 加载了 {len(rules)} 条规则")
        except ImportError:
            logger.warning("未安装 PyYAML，无法加载 YAML 规则文件")
        except Exception as e:
            logger.error(f"加载规则文件失败: {e}")
    
    def _create_default_rules(self) -> None:
        """创建默认规则。"""
        slow_request_threshold = self._defaults.get("slow_request_threshold", 1.0)
        slow_sql_threshold = self._defaults.get("slow_sql_threshold", 0.5)
        slow_request_exclude_paths = self._defaults.get("slow_request_exclude_paths") or None
        
        default_rules = [
            # 慢请求
            AlertRule(
                name="default_slow_request",
                event_types=[AlertEventType.SLOW_REQUEST],
                threshold=slow_request_threshold,
                aggregate_window=self._defaults.get("aggregate_window", 10),
                aggregate_threshold=self._defaults.get("slow_request_aggregate", 5),
                suppress_seconds=self._defaults.get("suppress_seconds", 300),
                exclude_paths=slow_request_exclude_paths,
            ),
            # 慢 SQL
            AlertRule(
                name="default_slow_sql",
                event_types=[AlertEventType.SLOW_SQL],
                threshold=slow_sql_threshold,
                aggregate_window=self._defaults.get("aggregate_window", 10),
                aggregate_threshold=self._defaults.get("slow_sql_aggregate", 5),
                suppress_seconds=self._defaults.get("suppress_seconds", 300),
            ),
            # 异常（立即告警）
            AlertRule(
                name="default_exception",
                event_types=[AlertEventType.EXCEPTION],
                aggregate_threshold=self._defaults.get("exception_aggregate", 1),
                suppress_seconds=self._defaults.get("suppress_seconds", 300),
            ),
            # 任务失败（立即告警）
            AlertRule(
                name="default_task_failure",
                event_types=[AlertEventType.TASK_FAILURE],
                aggregate_threshold=1,
                suppress_seconds=60,
            ),
            # 任务超时
            AlertRule(
                name="default_task_timeout",
                event_types=[AlertEventType.TASK_TIMEOUT],
                aggregate_threshold=1,
                suppress_seconds=300,
            ),
            # 自定义告警（立即告警）
            AlertRule(
                name="default_custom",
                event_types=[AlertEventType.CUSTOM],
                aggregate_threshold=1,
                suppress_seconds=self._defaults.get("suppress_seconds", 10),
            ),
        ]
        
        self._rules.extend(default_rules)
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则。
        
        Args:
            rule: 告警规则
        """
        self._rules.append(rule)
        self._aggregators[rule.name] = AlertAggregator(
            window_seconds=rule.aggregate_window,
            threshold=rule.aggregate_threshold,
            suppress_seconds=rule.suppress_seconds,
        )
    
    def register_notifier(self, name: str, notifier: "AlertNotifier") -> None:
        """注册通知器实例。
        
        Args:
            name: 通知器名称
            notifier: 通知器实例
        """
        self._notifiers[name] = notifier
    
    async def emit(self, event: AlertEvent) -> None:
        """发送告警事件。
        
        Args:
            event: 告警事件
        """
        if not self._enabled:
            return
        
        if not self._initialized:
            logger.warning("告警系统未初始化，跳过事件")
            return
        
        # 设置服务名
        if not event.service_name:
            event.service_name = self._service_name
        
        # 匹配规则
        for rule in self._rules:
            if rule.matches(event):
                aggregator = self._aggregators.get(rule.name)
                if aggregator and aggregator.should_alert(event):
                    await self._send_notification(rule, event, aggregator)
                break  # 只匹配第一个规则
    
    async def _send_notification(
        self,
        rule: AlertRule,
        event: AlertEvent,
        aggregator: AlertAggregator,
    ) -> None:
        """发送通知。"""
        # 获取聚合信息
        agg_info = aggregator.get_aggregation_info(event)
        
        # 构建通知
        notification = AlertNotification(
            title=self._build_title(event, agg_info["count"]),
            message=event.message,
            severity=event.severity,
            event_type=event.event_type,
            source=event.source,
            service_name=event.service_name,
            count=agg_info["count"],
            trace_ids=agg_info["trace_ids"],
            metadata=event.metadata,
        )
        
        # 发送到所有配置的通知器
        for notifier_name in rule.notifiers:
            notifier = self._notifiers.get(notifier_name)
            if notifier:
                # 异步发送，不阻塞
                asyncio.create_task(self._safe_send(notifier, notification))
            else:
                logger.warning(f"通知器不存在: {notifier_name}")
    
    async def _safe_send(self, notifier: "AlertNotifier", notification: AlertNotification) -> None:
        """安全发送通知（捕获异常）。"""
        try:
            await notifier.send(notification)
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    def _build_title(self, event: AlertEvent, count: int) -> str:
        """构建通知标题。"""
        type_names = {
            AlertEventType.SLOW_REQUEST: "慢请求",
            AlertEventType.SLOW_SQL: "慢SQL",
            AlertEventType.EXCEPTION: "异常",
            AlertEventType.TASK_FAILURE: "任务失败",
            AlertEventType.TASK_TIMEOUT: "任务超时",
            AlertEventType.CUSTOM: "告警",
        }
        type_name = type_names.get(event.event_type, "告警")
        
        if count > 1:
            return f"[{event.severity.value.upper()}] {type_name} x{count}"
        return f"[{event.severity.value.upper()}] {type_name}"
    
    @property
    def is_enabled(self) -> bool:
        """是否启用。"""
        return self._enabled
    
    @property
    def is_initialized(self) -> bool:
        """是否已初始化。"""
        return self._initialized


# 便捷函数
async def emit_alert(
    event_type: AlertEventType,
    message: str,
    *,
    severity: AlertSeverity = AlertSeverity.WARNING,
    trace_id: str | None = None,
    source: str | None = None,
    **metadata: Any,
) -> None:
    """发送告警事件的便捷函数。
    
    自动获取 trace_id 和检测来源。
    
    Args:
        event_type: 事件类型
        message: 告警消息
        severity: 严重级别
        trace_id: 追踪 ID（可选，自动获取）
        source: 来源（可选，自动检测）
        **metadata: 额外元数据
    
    示例：
        await emit_alert(
            AlertEventType.SLOW_SQL,
            "慢SQL查询",
            duration=2.5,
            sql="SELECT ...",
        )
    """
    from aury.boot.common.logging import get_trace_id
    
    if trace_id is None:
        trace_id = get_trace_id() or ""
    
    if source is None:
        source = _detect_source()
    
    event = AlertEvent(
        event_type=event_type,
        severity=severity,
        message=message,
        trace_id=trace_id,
        source=source,
        metadata=metadata,
    )
    
    manager = AlertManager.get_instance()
    await manager.emit(event)


def _detect_source() -> str:
    """检测当前执行来源。"""
    import inspect
    
    # 检查调用栈
    for frame_info in inspect.stack():
        module = frame_info.frame.f_globals.get("__name__", "")
        
        if "scheduler" in module.lower():
            return "scheduler"
        if "task" in module.lower() or "worker" in module.lower():
            return "task"
        if "middleware" in module.lower() or "api" in module.lower():
            return "api"
    
    return "unknown"


async def emit_exception_alert(
    exc: Exception,
    message: str | None = None,
    *,
    severity: AlertSeverity = AlertSeverity.ERROR,
    source: str | None = None,
    **metadata: Any,
) -> None:
    """发送异常告警的便捷函数（带完整堆栈）。
    
    用于在 try/except 中捕获异常后手动发送告警。
    框架只会自动告警未被捕获的异常，被 catch 的异常需要手动调用此函数。
    
    Args:
        exc: 异常对象
        message: 告警消息（默认使用异常信息）
        severity: 严重级别（默认 ERROR）
        source: 来源（可选，自动检测）
        **metadata: 额外元数据（如 session_id, user_id 等）
        
    Example:
        try:
            await some_operation()
        except Exception as e:
            await emit_exception_alert(
                e, 
                source="task_stream",
                session_id=session_id,
            )
            # 继续处理...
    """
    import traceback
    
    exc_type = type(exc).__name__
    exc_msg = str(exc)
    tb = traceback.format_exc()
    
    alert_message = message or f"{exc_type}: {exc_msg}"
    
    # 合并异常信息到 metadata
    metadata["error_type"] = exc_type
    metadata["error_message"] = exc_msg
    metadata["stacktrace"] = tb
    
    await emit_alert(
        AlertEventType.EXCEPTION,
        alert_message,
        severity=severity,
        source=source,
        **metadata,
    )


__all__ = [
    "AlertManager",
    "emit_alert",
    "emit_exception_alert",
]
