"""依赖注入容器 - 实现控制反转（IoC）。

提供依赖管理、生命周期控制和自动注入功能。
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import inspect
from typing import Any, TypeVar

from aury.boot.common.logging import logger

T = TypeVar("T")


class Lifetime(Enum):
    """服务生命周期。"""
    
    SINGLETON = "singleton"  # 单例，整个应用生命周期只创建一次
    SCOPED = "scoped"  # 作用域，每个作用域创建一次
    TRANSIENT = "transient"  # 瞬时，每次请求都创建新实例


class ServiceDescriptor:
    """服务描述符。
    
    记录服务的注册信息，包括类型、工厂函数和生命周期。
    """
    
    def __init__(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """初始化服务描述符。
        
        Args:
            service_type: 服务类型（通常是接口或抽象类）
            implementation: 实现类型（具体类）
            factory: 工厂函数
            lifetime: 生命周期
        """
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.lifetime = lifetime
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"<ServiceDescriptor "
            f"service={self.service_type.__name__} "
            f"impl={self.implementation.__name__} "
            f"lifetime={self.lifetime.value}>"
        )


class Container:
    """依赖注入容器（单例模式）。
    
    职责：
    1. 服务注册
    2. 依赖解析
    3. 生命周期管理
    4. 作用域管理
    
    使用示例:
        # 注册服务
        container = Container.get_instance()
        container.register(IUserRepository, UserRepository, Lifetime.SCOPED)
        container.register(UserService, lifetime=Lifetime.TRANSIENT)
        
        # 解析服务
        service = container.resolve(UserService)
        
        # 使用作用域
        with container.create_scope() as scope:
            service = scope.resolve(UserService)
    """
    
    _instance: Container | None = None
    
    def __init__(self) -> None:
        """私有构造函数，使用 get_instance() 获取实例。"""
        if Container._instance is not None:
            raise RuntimeError("Container 是单例类，请使用 get_instance() 获取实例")
        
        self._descriptors: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        logger.debug("依赖注入容器已创建")
    
    @classmethod
    def get_instance(cls) -> Container:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> Container:
        """注册服务。
        
        Args:
            service_type: 服务类型
            implementation: 实现类型
            factory: 工厂函数
            lifetime: 生命周期
            
        Returns:
            Container: 容器实例（支持链式调用）
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            lifetime=lifetime,
        )
        self._descriptors[service_type] = descriptor
        logger.debug(f"注册服务: {descriptor}")
        return self
    
    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册单例服务。
        
        Args:
            service_type: 服务类型
            implementation: 实现类型
            factory: 工厂函数
            
        Returns:
            Container: 容器实例（支持链式调用）
        """
        return self.register(service_type, implementation, factory, Lifetime.SINGLETON)
    
    def register_scoped(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册作用域服务。
        
        Args:
            service_type: 服务类型
            implementation: 实现类型
            factory: 工厂函数
            
        Returns:
            Container: 容器实例（支持链式调用）
        """
        return self.register(service_type, implementation, factory, Lifetime.SCOPED)
    
    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[..., T] | None = None,
    ) -> Container:
        """注册瞬时服务。
        
        Args:
            service_type: 服务类型
            implementation: 实现类型
            factory: 工厂函数
            
        Returns:
            Container: 容器实例（支持链式调用）
        """
        return self.register(service_type, implementation, factory, Lifetime.TRANSIENT)
    
    def register_instance(self, service_type: type[T], instance: T) -> Container:
        """注册实例（作为单例）。
        
        Args:
            service_type: 服务类型
            instance: 实例对象
            
        Returns:
            Container: 容器实例（支持链式调用）
        """
        self._singletons[service_type] = instance
        self._descriptors[service_type] = ServiceDescriptor(
            service_type=service_type,
            lifetime=Lifetime.SINGLETON,
        )
        logger.debug(f"注册实例: {service_type.__name__}")
        return self
    
    def resolve(self, service_type: type[T]) -> T:
        """解析服务。
        
        Args:
            service_type: 服务类型
            
        Returns:
            T: 服务实例
            
        Raises:
            ValueError: 服务未注册时抛出
        """
        # 检查是否已有单例实例
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # 获取服务描述符
        descriptor = self._descriptors.get(service_type)
        if descriptor is None:
            raise ValueError(f"服务未注册: {service_type.__name__}")
        
        # 创建实例
        instance = self._create_instance(descriptor)
        
        # 单例模式：缓存实例
        if descriptor.lifetime == Lifetime.SINGLETON:
            self._singletons[service_type] = instance
        
        return instance
    
    def _create_instance(self, descriptor: ServiceDescriptor, scope: Scope | None = None) -> Any:
        """创建服务实例。
        
        Args:
            descriptor: 服务描述符
            scope: 作用域（用于解析 SCOPED 类型的依赖）
            
        Returns:
            Any: 服务实例
        """
        # 使用工厂函数创建
        if descriptor.factory is not None:
            logger.debug(f"通过工厂创建: {descriptor.service_type.__name__}")
            # 工厂函数可以接收容器或作用域
            if scope is not None:
                return descriptor.factory(scope)
            return descriptor.factory(self)
        
        # 使用构造函数创建
        try:
            logger.debug(f"通过构造函数创建: {descriptor.implementation.__name__}")
            return descriptor.implementation()
        except TypeError:
            # 尝试自动注入依赖
            resolver = scope if scope is not None else self
            return self._create_with_dependencies(descriptor.implementation, resolver)
    
    def _create_with_dependencies(self, cls: type[T], resolver: Any = None) -> T:
        """创建实例并自动注入依赖。
        
        通过 inspect 获取构造函数参数，自动从容器解析依赖。
        
        Args:
            cls: 类型
            resolver: 解析器（Container 或 Scope），默认使用 self
            
        Returns:
            T: 实例
        """
        if resolver is None:
            resolver = self
            
        sig = inspect.signature(cls.__init__)
        params = sig.parameters
        
        # 跳过 self 参数
        args = []
        kwargs = {}
        
        for param_name, param in list(params.items())[1:]:  # 跳过 self
            param_type = param.annotation
            
            # 如果参数有类型注解且不是 Any
            if param_type != inspect.Parameter.empty and param_type != Any:
                try:
                    # 尝试从容器/作用域解析
                    dependency = resolver.resolve(param_type)
                    if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                        args.append(dependency)
                    else:
                        kwargs[param_name] = dependency
                except (ValueError, KeyError):
                    # 如果容器中没有，检查是否有默认值
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        logger.warning(
                            f"无法解析依赖 {param_name}: {param_type} "
                            f"在类 {cls.__name__} 中，使用默认值 None"
                        )
                        kwargs[param_name] = None
        
        logger.debug(f"自动注入依赖: {cls.__name__} args={len(args)} kwargs={list(kwargs.keys())}")
        return cls(*args, **kwargs)
    
    def create_scope(self) -> Scope:
        """创建作用域。
        
        Returns:
            Scope: 作用域对象
        """
        return Scope(self)
    
    def clear(self) -> None:
        """清空容器。"""
        self._descriptors.clear()
        self._singletons.clear()
        logger.debug("容器已清空")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return (
            f"<Container "
            f"services={len(self._descriptors)} "
            f"singletons={len(self._singletons)}>"
        )


class Scope:
    """依赖注入作用域。
    
    管理作用域内服务的生命周期。
    """
    
    def __init__(self, container: Container) -> None:
        """初始化作用域。
        
        Args:
            container: 容器实例
        """
        self._container = container
        self._scoped_instances: dict[type, Any] = {}
        logger.debug("作用域已创建")
    
    def resolve(self, service_type: type[T]) -> T:
        """解析服务。
        
        Args:
            service_type: 服务类型
            
        Returns:
            T: 服务实例
        """
        descriptor = self._container._descriptors.get(service_type)
        if descriptor is None:
            raise ValueError(f"服务未注册: {service_type.__name__}")
        
        # 单例：从容器获取
        if descriptor.lifetime == Lifetime.SINGLETON:
            return self._container.resolve(service_type)
        
        # 作用域：从作用域缓存获取
        if descriptor.lifetime == Lifetime.SCOPED:
            if service_type not in self._scoped_instances:
                self._scoped_instances[service_type] = self._container._create_instance(descriptor, scope=self)
            return self._scoped_instances[service_type]
        
        # 瞬时：每次创建新实例
        return self._container._create_instance(descriptor, scope=self)
    
    def __enter__(self) -> Scope:
        """进入作用域。"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出作用域。"""
        self._scoped_instances.clear()
        logger.debug("作用域已销毁")
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"<Scope instances={len(self._scoped_instances)}>"


__all__ = [
    "Container",
    "Lifetime",
    "Scope",
    "ServiceDescriptor",
]

