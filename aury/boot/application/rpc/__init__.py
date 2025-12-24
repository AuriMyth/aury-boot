"""RPC调用框架。

提供统一的微服务RPC调用接口。

基于 toolkit/http 的 HttpClient，提供 RPC 调用封装。
支持多种服务发现方式（通过 BaseConfig.rpc_client 配置）：
- 配置文件（BaseConfig.rpc_client.services，优先级最高）
- DNS 解析（统一处理 K8s/Docker Compose，自动使用服务名）

注意：负载均衡由基础设施层（K8s Service、Docker Compose）自动处理，
应用层仅负责服务发现和调用，不实现负载均衡策略。

使用示例:
    # 方式1：使用服务发现（推荐）
    from aury.boot.application.config import BaseConfig
    from aury.boot.application.rpc import create_rpc_client
    
    config = BaseConfig()  # 从环境变量和 .env 文件加载配置
    client = create_rpc_client(service_name="user-service", config=config)
    response = await client.get("/api/v1/users/1")
    
    # 方式2：直接指定 URL（不使用服务发现）
    from aury.boot.application.rpc import RPCClient
    
    client = RPCClient(base_url="http://user-service:8000")
    response = await client.get("/api/v1/users/1")
    
    配置方式（通过环境变量或 .env 文件）:
    # 调用配置（RPC_CLIENT_ 前缀）
    RPC_CLIENT_SERVICES={"user-service": "http://user-service:8000"}
    RPC_CLIENT_DNS_SCHEME=http
    RPC_CLIENT_DNS_PORT=80
    
    # 注册配置（RPC_SERVICE_ 前缀）
    RPC_SERVICE_NAME=my-service
    RPC_SERVICE_URL=http://my-service:8000
"""

from .base import BaseRPCClient, RPCError, RPCResponse
from .client import RPCClient, create_rpc_client
from .discovery import (
    CompositeServiceDiscovery,
    ConfigServiceDiscovery,
    DNSServiceDiscovery,
    ServiceDiscovery,
    get_service_discovery,
    set_service_discovery,
)

__all__ = [
    "BaseRPCClient",
    "CompositeServiceDiscovery",
    "ConfigServiceDiscovery",
    "DNSServiceDiscovery",
    "RPCClient",
    "RPCError",
    "RPCResponse",
    "ServiceDiscovery",
    "create_rpc_client",
    "get_service_discovery",
    "set_service_discovery",
]

