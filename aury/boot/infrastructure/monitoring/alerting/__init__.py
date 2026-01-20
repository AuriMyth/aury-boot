"""告警系统模块。

提供企业级告警通知功能：
- 慢请求、慢SQL、异常自动告警
- 累计触发和抑制机制
- 可扩展的通知渠道（内置飞书、Webhook）

快速开始：
    1. 配置环境变量
        ALERT_ENABLED=true
        ALERT_NOTIFIER_FEISHU_WEBHOOK=https://open.feishu.cn/...
    
    2. 在应用启动时初始化（FoundationApp 自动处理）
    
    3. 可选：添加规则文件 alert_rules.yaml

使用便捷函数发送自定义告警：
    from aury.boot.infrastructure.monitoring.alerting import emit_alert, AlertEventType
    
    await emit_alert(
        AlertEventType.CUSTOM,
        "自定义告警消息",
        severity=AlertSeverity.WARNING,
        my_data="xxx",
    )
"""

from .aggregator import AlertAggregator
from .events import AlertEvent, AlertEventType, AlertNotification, AlertSeverity
from .manager import AlertManager, emit_alert, emit_exception_alert
from .notifiers import AlertNotifier, FeishuNotifier, WebhookNotifier
from .rules import AlertRule, load_rules_from_dict

__all__ = [
    # 核心类
    "AlertAggregator",
    "AlertEvent",
    "AlertEventType",
    "AlertManager",
    "AlertNotification",
    "AlertRule",
    "AlertSeverity",
    # 通知器
    "AlertNotifier",
    "FeishuNotifier",
    "WebhookNotifier",
    # 便捷函数
    "emit_alert",
    "emit_exception_alert",
    "load_rules_from_dict",
]
