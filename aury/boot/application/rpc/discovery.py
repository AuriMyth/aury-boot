"""服务发现模块。

支持多种服务发现方式：
- 配置文件（推荐，通过 BaseConfig.rpc_client.services）
- DNS 解析（统一处理 K8s/Docker Compose，通过服务名自动解析）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aury.boot.common.logging import logger

if TYPE_CHECKING:
    from aury.boot.application.config import BaseConfig


class ServiceDiscovery:
    """服务发现抽象基类。
    
    所有服务发现实现都应该继承此类。
    """
    
    def resolve(self, service_name: str) -> str | None:
        """解析服务地址。
        
        Args:
            service_name: 服务名称
            
        Returns:
            str | None: 服务地址（URL），如果无法解析返回 None
        """
        raise NotImplementedError


class ConfigServiceDiscovery(ServiceDiscovery):
    """基于配置文件的服务发现。
    
    从配置文件中读取服务地址映射。
    
    配置格式：
    ```python
    services = {
        "user-service": "http://user-service:8000",
        "order-service": "http://order-service:8001",
    }
    ```
    """
    
    def __init__(self, service_config: dict[str, str] | None = None) -> None:
        """初始化配置服务发现。
        
        Args:
            service_config: 服务配置字典 {service_name: url}
        """
        self._services: dict[str, str] = service_config or {}
    
    def resolve(self, service_name: str) -> str | None:
        """从配置中解析服务地址。"""
        url = self._services.get(service_name)
        if url:
            logger.debug(f"从配置解析服务: {service_name} -> {url}")
            return url
        logger.warning(f"配置中未找到服务: {service_name}")
        return None
    
    def register(self, service_name: str, url: str) -> None:
        """注册服务地址。
        
        Args:
            service_name: 服务名称
            url: 服务地址
        """
        self._services[service_name] = url
        logger.info(f"注册服务: {service_name} -> {url}")




class DNSServiceDiscovery(ServiceDiscovery):
    """DNS 服务发现（统一处理 K8s/Docker Compose）。
    
    直接使用服务名进行 DNS 解析：
    - K8s: 自动使用 service-name（K8s DNS 会在同一 namespace 内解析）
    - Docker Compose: 直接使用 service-name
    """
    
    def __init__(
        self,
        scheme: str = "http",
        default_port: int = 80,
    ) -> None:
        """初始化 DNS 服务发现。
        
        Args:
            scheme: 协议（http 或 https）
            default_port: 默认端口
        """
        self._scheme = scheme
        self._default_port = default_port
    
    def resolve(self, service_name: str) -> str | None:
        """使用 DNS 解析服务地址。
        
        Args:
            service_name: 服务名称（直接作为主机名，DNS 自动解析）
        """
        # 直接使用服务名作为主机名（DNS 自动处理）
        url = f"{self._scheme}://{service_name}"
        
        if self._default_port not in (80, 443):
            url = f"{url}:{self._default_port}"
        
        logger.debug(f"使用 DNS 解析服务: {service_name} -> {url}")
        return url


class CompositeServiceDiscovery(ServiceDiscovery):
    """组合服务发现。
    
    按优先级顺序尝试多种服务发现方式：
    1. 配置文件（最高优先级，通过 BaseConfig.rpc_client.services）
    2. DNS 解析（统一处理 K8s/Docker Compose，自动检测环境）
    """
    
    def __init__(
        self,
        config: "BaseConfig" | None = None,
    ) -> None:
        """初始化组合服务发现。
        
        Args:
            config: 应用配置（BaseConfig），如果为 None，则仅使用默认配置
        """
        self._discoveries: list[ServiceDiscovery] = []
        
        # 从配置中获取 RPC 客户端设置
        if config:
            rpc_client_settings = config.rpc_client
        else:
            # 如果没有提供配置，使用默认配置
            from aury.boot.application.config import RPCClientSettings
            rpc_client_settings = RPCClientSettings()
        
        # 1. 配置文件（最高优先级）
        if rpc_client_settings.services:
            self._discoveries.append(ConfigServiceDiscovery(rpc_client_settings.services))
        
        # 2. DNS 解析（如果启用）
        if rpc_client_settings.use_dns_fallback:
            logger.info("启用 DNS 服务发现（统一处理 K8s/Docker Compose）")
            self._discoveries.append(
                DNSServiceDiscovery(
                    scheme=rpc_client_settings.dns_scheme,
                    default_port=rpc_client_settings.dns_port,
                )
            )
    
    def resolve(self, service_name: str) -> str | None:
        """按优先级顺序解析服务地址。"""
        for discovery in self._discoveries:
            url = discovery.resolve(service_name)
            if url:
                return url
        
        logger.error(f"无法解析服务地址: {service_name}（已尝试所有服务发现方式）")
        return None


# 全局服务发现实例
_global_discovery: ServiceDiscovery | None = None
_global_config: "BaseConfig | None" = None


def get_service_discovery(config: "BaseConfig | None" = None) -> ServiceDiscovery:
    """获取全局服务发现实例。
    
    如果未初始化，使用配置创建组合服务发现。
    
    Args:
        config: 应用配置（可选），如果提供则使用此配置初始化
    
    Returns:
        ServiceDiscovery: 服务发现实例
    """
    global _global_discovery, _global_config
    
    # 如果提供了新配置，更新全局配置
    if config is not None:
        _global_config = config
    
    # 如果未初始化或配置已更新，重新创建
    if _global_discovery is None or config is not None:
        _global_discovery = CompositeServiceDiscovery(_global_config)
    
    return _global_discovery


def set_service_discovery(discovery: ServiceDiscovery) -> None:
    """设置全局服务发现实例。
    
    Args:
        discovery: 服务发现实例
    """
    global _global_discovery
    _global_discovery = discovery
    logger.info("已设置全局服务发现实例")


__all__ = [
    "CompositeServiceDiscovery",
    "ConfigServiceDiscovery",
    "DNSServiceDiscovery",
    "ServiceDiscovery",
    "get_service_discovery",
    "set_service_discovery",
]

