"""服务注册中心。

支持服务发现和负载均衡。
"""

from __future__ import annotations

import random
from typing import Optional

from aurimyth.foundation_kit.common.logging import logger


class ServiceRegistry:
    """服务注册中心。

    管理服务实例列表，支持负载均衡。
    """

    def __init__(self) -> None:
        """初始化服务注册中心。"""
        self._services: dict[str, list[str]] = {}

    def register(self, service_name: str, instance_url: str) -> None:
        """注册服务实例。

        Args:
            service_name: 服务名称
            instance_url: 实例URL
        """
        if service_name not in self._services:
            self._services[service_name] = []
        
        if instance_url not in self._services[service_name]:
            self._services[service_name].append(instance_url)
            logger.info(f"注册服务实例: {service_name} -> {instance_url}")

    def unregister(self, service_name: str, instance_url: str) -> None:
        """注销服务实例。

        Args:
            service_name: 服务名称
            instance_url: 实例URL
        """
        if service_name in self._services and instance_url in self._services[service_name]:  # noqa: SIM102
                self._services[service_name].remove(instance_url)
                logger.info(f"注销服务实例: {service_name} -> {instance_url}")

    def get_instance(self, service_name: str, strategy: str = "random") -> str | None:
        """获取服务实例（负载均衡）。

        Args:
            service_name: 服务名称
            strategy: 负载均衡策略（random, round_robin）

        Returns:
            Optional[str]: 服务实例URL，如果不存在返回None
        """
        if service_name not in self._services or not self._services[service_name]:
            logger.warning(f"服务实例不存在: {service_name}")
            return None

        instances = self._services[service_name]
        
        if strategy == "random":
            return random.choice(instances)
        elif strategy == "round_robin":
            # 简单的轮询（实际应该用更复杂的实现）
            return instances[0]
        else:
            return instances[0]

    def get_all_instances(self, service_name: str) -> list[str]:
        """获取所有服务实例。

        Args:
            service_name: 服务名称

        Returns:
            list[str]: 服务实例URL列表
        """
        return self._services.get(service_name, [])

    def health_check(self, service_name: str, instance_url: str) -> bool:
        """健康检查（简单实现）。

        Args:
            service_name: 服务名称
            instance_url: 实例URL

        Returns:
            bool: 是否健康
        """
        # 简单实现，实际应该发送HTTP请求检查
        return instance_url in self._services.get(service_name, [])


# 全局服务注册中心实例
_service_registry = ServiceRegistry()


def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册中心实例。"""
    return _service_registry

