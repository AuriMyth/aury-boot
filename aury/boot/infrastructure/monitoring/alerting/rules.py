"""告警规则定义。

定义告警规则数据结构和匹配逻辑。
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .events import AlertEventType, AlertSeverity

if TYPE_CHECKING:
    from .events import AlertEvent


@dataclass
class AlertRule:
    """告警规则。
    
    定义何时触发告警、如何聚合、发送到哪些通知器。
    
    示例：
        # 慢请求规则：1分钟内5次触发，5分钟抑制
        rule = AlertRule(
            name="slow_request",
            event_types=[AlertEventType.SLOW_REQUEST],
            threshold=1.0,
            aggregate_window=60,
            aggregate_threshold=5,
            suppress_seconds=300,
            notifiers=["feishu"],
        )
        
        # 关键接口规则：更严格的阈值
        rule = AlertRule(
            name="critical_api",
            event_types=[AlertEventType.SLOW_REQUEST],
            path_pattern="/api/v1/payments/*",
            threshold=0.5,
            aggregate_threshold=1,
            notifiers=["feishu", "sms"],
        )
    """
    
    name: str
    event_types: list[AlertEventType]
    
    # 触发条件
    threshold: float | None = None          # 慢阈值（秒），仅对 slow_* 类型有效
    severity_min: AlertSeverity = AlertSeverity.WARNING
    
    # 过滤条件
    source_filter: str | None = None        # api / task / scheduler
    path_pattern: str | None = None         # 路径匹配（支持 * 通配符）
    exclude_paths: list[str] | None = None  # 排除路径列表（支持 * 通配符）
    
    # 聚合配置
    aggregate_window: int = 10              # 滑动窗口（秒）
    aggregate_threshold: int = 1            # 触发阈值
    suppress_seconds: int = 300             # 抑制时间（秒）
    
    # 通知配置
    notifiers: list[str] = field(default_factory=lambda: ["default"])
    
    # 编译后的正则（内部使用）
    _path_regex: re.Pattern | None = field(default=None, repr=False)
    _exclude_regexes: list[re.Pattern] = field(default_factory=list, repr=False)
    
    def __post_init__(self) -> None:
        """初始化后编译路径正则。"""
        if self.path_pattern:
            # 将通配符转换为正则
            regex_pattern = fnmatch.translate(self.path_pattern)
            self._path_regex = re.compile(regex_pattern)
        
        if self.exclude_paths:
            # 编译所有排除路径的正则
            for exclude_pattern in self.exclude_paths:
                regex_pattern = fnmatch.translate(exclude_pattern)
                self._exclude_regexes.append(re.compile(regex_pattern))
    
    def matches(self, event: "AlertEvent") -> bool:
        """检查事件是否匹配规则。
        
        Args:
            event: 告警事件
        
        Returns:
            bool: 是否匹配
        """
        # 检查事件类型
        if event.event_type not in self.event_types:
            return False
        
        # 检查严重级别
        severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]
        if severity_order.index(event.severity) < severity_order.index(self.severity_min):
            return False
        
        # 检查来源
        if self.source_filter and event.source != self.source_filter:
            return False
        
        # 检查路径
        if self._path_regex:
            endpoint = event.metadata.get("endpoint", "")
            if not self._path_regex.fullmatch(endpoint):
                return False
        
        # 检查排除路径
        if self._exclude_regexes:
            endpoint = event.metadata.get("endpoint", "")
            for exclude_regex in self._exclude_regexes:
                if exclude_regex.fullmatch(endpoint):
                    return False  # 匹配到排除规则，不触发告警
        
        # 检查阈值（对于 slow_* 类型）
        if self.threshold is not None and event.event_type in (
            AlertEventType.SLOW_REQUEST,
            AlertEventType.SLOW_SQL,
        ):
            duration = event.metadata.get("duration", 0)
            if duration < self.threshold:
                return False
        
        return True


def load_rules_from_dict(data: dict) -> tuple[dict, list[AlertRule]]:
    """从字典加载规则配置。
    
    Args:
        data: 规则配置字典（通常从 YAML 加载）
    
    Returns:
        (defaults, rules) 元组
    """
    defaults = data.get("defaults", {})
    rules = []
    
    for rule_data in data.get("rules", []):
        # 解析事件类型
        event_types = []
        for et in rule_data.get("event_types", []):
            if isinstance(et, str):
                event_types.append(AlertEventType(et))
            else:
                event_types.append(et)
        
        # 解析严重级别
        severity_min = rule_data.get("severity_min", defaults.get("severity_min", "warning"))
        if isinstance(severity_min, str):
            severity_min = AlertSeverity(severity_min.lower())
        
        rule = AlertRule(
            name=rule_data["name"],
            event_types=event_types,
            threshold=rule_data.get("threshold", defaults.get("threshold")),
            severity_min=severity_min,
            source_filter=rule_data.get("source_filter") or rule_data.get("source"),
            path_pattern=rule_data.get("path_pattern"),
            exclude_paths=rule_data.get("exclude_paths"),
            aggregate_window=rule_data.get("aggregate_window", defaults.get("aggregate_window", 10)),
            aggregate_threshold=rule_data.get("aggregate_threshold", defaults.get("aggregate_threshold", 1)),
            suppress_seconds=rule_data.get("suppress_seconds", defaults.get("suppress_seconds", 300)),
            notifiers=rule_data.get("notifiers", ["default"]),
        )
        rules.append(rule)
    
    return defaults, rules


__all__ = [
    "AlertRule",
    "load_rules_from_dict",
]
