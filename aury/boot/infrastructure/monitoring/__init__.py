"""性能监控模块。

提供组件化的性能监控功能，支持自定义监控管道和组件。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
import time

from aury.boot.common.logging import logger


class MonitorContext:
    """监控上下文。
    
    包含方法执行的上下文信息，供监控组件使用。
    """
    
    def __init__(
        self,
        func_name: str,
        service_name: str,
        start_time: float,
        duration: float | None = None,
        call_count: int | None = None,
        exception: Exception | None = None,
    ) -> None:
        """初始化监控上下文。
        
        Args:
            func_name: 方法全名
            service_name: 服务类名
            start_time: 开始时间
            duration: 执行时长（秒）
            call_count: 调用次数
            exception: 异常对象（如果有）
        """
        self.func_name = func_name
        self.service_name = service_name
        self.start_time = start_time
        self.duration = duration
        self.call_count = call_count
        self.exception = exception


class MonitorComponent(ABC):
    """监控组件接口。
    
    所有监控组件都应该实现此接口。
    """
    
    @abstractmethod
    async def process(self, context: MonitorContext) -> None:
        """处理监控上下文。
        
        Args:
            context: 监控上下文
        """
        pass


class CallCounterComponent(MonitorComponent):
    """调用次数统计组件。"""
    
    def __init__(self) -> None:
        """初始化调用计数器组件。"""
        self._counters: dict[str, int] = {}
    
    async def process(self, context: MonitorContext) -> None:
        """更新调用次数。
        
        Args:
            context: 监控上下文
        """
        self._counters[context.func_name] = self._counters.get(context.func_name, 0) + 1
        context.call_count = self._counters[context.func_name]
    
    def get_count(self, func_name: str) -> int:
        """获取方法的调用次数。
        
        Args:
            func_name: 方法全名
        
        Returns:
            int: 调用次数
        """
        return self._counters.get(func_name, 0)
    
    def reset(self) -> None:
        """重置所有计数器。"""
        self._counters.clear()


class SlowMethodDetectorComponent(MonitorComponent):
    """慢方法检测组件。
    
    检测执行时间超过阈值的方法并记录警告。
    支持可选的告警通知（飞书/Webhook）。
    """
    
    def __init__(self, threshold: float, *, alert: bool = False) -> None:
        """初始化慢方法检测组件。
        
        Args:
            threshold: 慢方法阈值（秒）
            alert: 是否发送告警通知
        """
        self._threshold = threshold
        self._alert = alert
    
    async def process(self, context: MonitorContext) -> None:
        """检测慢方法。
        
        Args:
            context: 监控上下文
        """
        if context.duration is not None and context.duration >= self._threshold:
            logger.warning(
                f"慢方法检测: {context.func_name} 执行时间 {context.duration:.3f}s "
                f"(阈值: {self._threshold}s)"
            )
            
            # 发送告警通知
            if self._alert:
                await self._emit_alert(context)


    async def _emit_alert(self, context: MonitorContext) -> None:
        """发送慢方法告警。"""
        try:
            from aury.boot.infrastructure.monitoring.alerting import (
                AlertEventType,
                AlertSeverity,
                emit_alert,
            )
            
            await emit_alert(
                AlertEventType.CUSTOM,
                f"慢方法: {context.func_name}",
                severity=AlertSeverity.WARNING,
                source="service",
                duration=context.duration,
                threshold=self._threshold,
                service=context.service_name,
            )
        except ImportError:
            pass  # alerting 模块未加载
        except Exception as e:
            logger.debug(f"发送慢方法告警失败: {e}")


# =============================================================================
# HTTP 请求监控
# =============================================================================


async def monitor_http_request(
    *,
    method: str,
    path: str,
    duration: float,
    status_code: int,
    threshold: float = 1.0,
    alert: bool = False,
    trace_id: str = "",
    exception: Exception | None = None,
) -> None:
    """监控 HTTP 请求。
    
    由 middleware 调用，统一处理 HTTP 请求的慢请求检测和告警。
    
    Args:
        method: HTTP 方法
        path: 请求路径
        duration: 执行时间（秒）
        status_code: 响应状态码
        threshold: 慢请求阈值（秒）
        alert: 是否发送告警
        trace_id: 追踪 ID
        exception: 异常对象（如果有）
    """
    # 慢请求检测和告警
    if duration >= threshold:
        if alert:
            await _emit_http_slow_alert(
                method=method,
                path=path,
                duration=duration,
                threshold=threshold,
                trace_id=trace_id,
            )
    
    # 异常告警
    if exception is not None and alert:
        await _emit_http_exception_alert(
            method=method,
            path=path,
            duration=duration,
            exception=exception,
            trace_id=trace_id,
        )


async def _emit_http_slow_alert(
    method: str,
    path: str,
    duration: float,
    threshold: float,
    trace_id: str,
) -> None:
    """发送 HTTP 慢请求告警。"""
    try:
        from aury.boot.infrastructure.monitoring.alerting import (
            AlertEventType,
            AlertSeverity,
            emit_alert,
        )
        
        await emit_alert(
            AlertEventType.SLOW_REQUEST,
            f"慢请求: {method} {path}",
            severity=AlertSeverity.WARNING,
            trace_id=trace_id,
            source="api",
            duration=duration,
            threshold=threshold,
            endpoint=path,
            method=method,
        )
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"发送慢请求告警失败: {e}")


async def _emit_http_exception_alert(
    method: str,
    path: str,
    duration: float,
    exception: Exception,
    trace_id: str,
) -> None:
    """发送 HTTP 异常告警。"""
    try:
        from aury.boot.infrastructure.monitoring.alerting import (
            AlertEventType,
            AlertSeverity,
            emit_alert,
        )
        
        await emit_alert(
            AlertEventType.EXCEPTION,
            f"请求异常: {method} {path} - {type(exception).__name__}: {exception}",
            severity=AlertSeverity.ERROR,
            trace_id=trace_id,
            source="api",
            duration=duration,
            endpoint=path,
            method=method,
            error_type=type(exception).__name__,
            error_message=str(exception),
        )
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"发送异常告警失败: {e}")


# =============================================================================
# Service 方法监控组件
# =============================================================================


class StandardMetricsReporterComponent(MonitorComponent):
    """标准指标报告组件。
    
    使用标准日志格式报告性能指标。
    """
    
    async def process(self, context: MonitorContext) -> None:
        """报告性能指标。
        
        Args:
            context: 监控上下文
        """
        if context.duration is not None and context.call_count is not None:
            logger.debug(
                f"性能指标: {context.func_name} | "
                f"执行时间: {context.duration:.3f}s | "
                f"调用次数: {context.call_count}"
            )


class PrometheusMetricsReporterComponent(MonitorComponent):
    """Prometheus 格式指标报告组件。
    
    使用 Prometheus 格式报告性能指标。
    """
    
    async def process(self, context: MonitorContext) -> None:
        """报告 Prometheus 格式指标。
        
        Args:
            context: 监控上下文
        """
        if context.duration is not None and context.call_count is not None:
            logger.info(
                f"# TYPE service_method_duration_seconds histogram\n"
                f"service_method_duration_seconds{{"
                f"method=\"{context.func_name}\","
                f"service=\"{context.service_name}\""
                f"}} {context.duration:.6f}\n"
                f"# TYPE service_method_calls_total counter\n"
                f"service_method_calls_total{{"
                f"method=\"{context.func_name}\","
                f"service=\"{context.service_name}\""
                f"}} {context.call_count}"
            )


class ErrorReporterComponent(MonitorComponent):
    """错误报告组件。
    
    报告方法执行失败的错误信息。
    支持可选的告警通知（飞书/Webhook）。
    """
    
    def __init__(self, *, alert: bool = False) -> None:
        """初始化错误报告组件。
        
        Args:
            alert: 是否发送告警通知
        """
        self._alert = alert
    
    async def process(self, context: MonitorContext) -> None:
        """报告错误信息。
        
        Args:
            context: 监控上下文
        """
        if context.exception is not None and context.duration is not None:
            logger.error(
                f"方法执行失败: {context.func_name} | "
                f"执行时间: {context.duration:.3f}s | "
                f"异常: {type(context.exception).__name__}: {context.exception}"
            )
            
            # 发送告警通知
            if self._alert:
                await self._emit_alert(context)
    
    async def _emit_alert(self, context: MonitorContext) -> None:
        """发送异常告警。"""
        try:
            from aury.boot.infrastructure.monitoring.alerting import (
                AlertEventType,
                AlertSeverity,
                emit_alert,
            )
            
            await emit_alert(
                AlertEventType.EXCEPTION,
                f"方法异常: {context.func_name}",
                severity=AlertSeverity.ERROR,
                source="service",
                duration=context.duration,
                service=context.service_name,
                exception_type=type(context.exception).__name__,
                exception_message=str(context.exception),
            )
        except ImportError:
            pass  # alerting 模块未加载
        except Exception as e:
            logger.debug(f"发送异常告警失败: {e}")


class MonitorPipeline:
    """监控管道。
    
    组合多个监控组件，按顺序执行。
    """
    
    def __init__(self, *components: MonitorComponent) -> None:
        """初始化监控管道。
        
        Args:
            *components: 监控组件列表
        """
        self._components = list(components)
    
    def add_component(self, component: MonitorComponent) -> MonitorPipeline:
        """添加监控组件。
        
        Args:
            component: 监控组件
        
        Returns:
            MonitorPipeline: 管道实例（支持链式调用）
        """
        self._components.append(component)
        return self
    
    def add_components(self, *components: MonitorComponent) -> MonitorPipeline:
        """批量添加监控组件。
        
        Args:
            *components: 监控组件列表
        
        Returns:
            MonitorPipeline: 管道实例（支持链式调用）
        """
        self._components.extend(components)
        return self
    
    async def execute(self, context: MonitorContext) -> None:
        """执行所有监控组件。
        
        Args:
            context: 监控上下文
        """
        for component in self._components:
            await component.process(context)
    
    def __len__(self) -> int:
        """返回组件数量。"""
        return len(self._components)
    
    def __iter__(self):
        """迭代组件。"""
        return iter(self._components)


# 全局调用计数器组件实例（所有装饰器共享，用于统计全局调用次数）
_global_call_counter = CallCounterComponent()


class MonitorPipelineBuilder:
    """监控管道构建器。
    
    提供便捷的方法构建监控管道。
    """
    
    def __init__(self) -> None:
        """初始化构建器。"""
        self._components: list[MonitorComponent] = []
    
    def with_call_counter(
        self,
        counter: CallCounterComponent | None = None,
    ) -> MonitorPipelineBuilder:
        """添加调用次数统计组件。
        
        Args:
            counter: 调用计数器组件，如果为 None 则使用全局实例
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        if counter is None:
            counter = _global_call_counter
        self._components.append(counter)
        return self
    
    def with_slow_detector(
        self,
        threshold: float = 1.0,
        *,
        alert: bool = False,
        detector: SlowMethodDetectorComponent | None = None,
    ) -> MonitorPipelineBuilder:
        """添加慢方法检测组件。
        
        Args:
            threshold: 慢方法阈值（秒）
            alert: 是否发送告警通知
            detector: 慢方法检测组件，如果为 None 则创建新实例
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        if detector is None:
            detector = SlowMethodDetectorComponent(threshold, alert=alert)
        self._components.append(detector)
        return self
    
    def with_metrics_reporter(
        self,
        prometheus_format: bool = False,
        reporter: MonitorComponent | None = None,
    ) -> MonitorPipelineBuilder:
        """添加指标报告组件。
        
        Args:
            prometheus_format: 是否使用 Prometheus 格式
            reporter: 报告组件，如果为 None 则根据 prometheus_format 创建
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        if reporter is None:
            if prometheus_format:
                reporter = PrometheusMetricsReporterComponent()
            else:
                reporter = StandardMetricsReporterComponent()
        self._components.append(reporter)
        return self
    
    def with_error_reporter(
        self,
        *,
        alert: bool = False,
        reporter: ErrorReporterComponent | None = None,
    ) -> MonitorPipelineBuilder:
        """添加错误报告组件。
        
        Args:
            alert: 是否发送告警通知
            reporter: 错误报告组件，如果为 None 则创建新实例
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        if reporter is None:
            reporter = ErrorReporterComponent(alert=alert)
        self._components.append(reporter)
        return self
    
    def with_component(self, component: MonitorComponent) -> MonitorPipelineBuilder:
        """添加自定义组件。
        
        Args:
            component: 监控组件
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        self._components.append(component)
        return self
    
    def with_components(self, *components: MonitorComponent) -> MonitorPipelineBuilder:
        """批量添加自定义组件。
        
        Args:
            *components: 监控组件列表
        
        Returns:
            MonitorPipelineBuilder: 构建器实例（支持链式调用）
        """
        self._components.extend(components)
        return self
    
    def build(self) -> MonitorPipeline:
        """构建监控管道。
        
        Returns:
            MonitorPipeline: 监控管道实例
        """
        return MonitorPipeline(*self._components)


def monitor(
    slow_threshold: float = 1.0,
    metrics: bool = True,
    prometheus_format: bool = False,
    alert: bool = False,
    pipeline: MonitorPipeline | None = None,
    components: list[MonitorComponent] | None = None,
    pipeline_builder: Callable[[], MonitorPipeline] | None = None,
) -> Callable:
    """服务层性能监控装饰器。
    
    监控服务方法的执行时间和调用次数。
    支持慢方法警告、Prometheus 格式导出和告警通知。
    支持自定义监控管道和组件。
    
    Args:
        slow_threshold: 慢方法阈值（秒），默认 1.0 秒
        metrics: 是否记录指标（执行时间、调用次数），默认 True
        prometheus_format: 是否使用 Prometheus 格式记录指标，默认 False
        alert: 是否发送告警通知（飞书/Webhook），默认 False
        pipeline: 自定义监控管道，如果提供则忽略其他参数
        components: 自定义组件列表，如果提供则使用这些组件构建管道
        pipeline_builder: 自定义管道构建函数，如果提供则使用此函数构建管道
    
    用法:
        # 基础用法
        class UserService(BaseService):
            @monitor(slow_threshold=0.5, metrics=True)
            async def create_user(self, data: dict):
                return await self.user_repo.create(data)
        
        # 启用告警通知
        class PaymentService(BaseService):
            @monitor(slow_threshold=0.5, alert=True)
            async def process_payment(self, order_id: str):
                ...
        
        # 使用自定义组件
        custom_component = MyCustomMonitorComponent()
        @monitor(components=[custom_component])
        async def custom_method(self):
            pass
        
        # 使用自定义管道
        custom_pipeline = MonitorPipeline(
            CallCounterComponent(),
            SlowMethodDetectorComponent(0.5),
            MyCustomReporterComponent(),
        )
        @monitor(pipeline=custom_pipeline)
        async def advanced_method(self):
            pass
        
        # 使用管道构建器
        def build_custom_pipeline():
            return (MonitorPipelineBuilder()
                .with_call_counter()
                .with_slow_detector(threshold=0.3)
                .with_component(MyCustomComponent())
                .build())
        
        @monitor(pipeline_builder=build_custom_pipeline)
        async def builder_method(self):
            pass
    """
    
    # 确定使用的管道
    if pipeline is not None:
        # 使用提供的管道
        monitor_pipeline = pipeline
    elif pipeline_builder is not None:
        # 使用构建器函数
        monitor_pipeline = pipeline_builder()
    elif components is not None:
        # 使用提供的组件列表
        monitor_pipeline = MonitorPipeline(*components)
    else:
        # 使用默认构建逻辑
        builder = MonitorPipelineBuilder()
        
        if metrics:
            builder.with_call_counter()
        
        builder.with_slow_detector(threshold=slow_threshold, alert=alert)
        
        if metrics:
            builder.with_metrics_reporter(prometheus_format=prometheus_format)
        
        builder.with_error_reporter(alert=alert)
        
        monitor_pipeline = builder.build()
    
    def decorator(func: Callable) -> Callable:
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            context = MonitorContext(
                func_name=func_name,
                service_name=self.__class__.__name__,
                start_time=start_time,
            )
            
            try:
                # 执行方法
                result = await func(self, *args, **kwargs)
                
                # 计算执行时间
                context.duration = time.time() - start_time
                
                # 更新调用次数（如果管道中有调用计数器）
                for component in monitor_pipeline:
                    if isinstance(component, CallCounterComponent):
                        context.call_count = component.get_count(func_name)
                        break
                
                # 执行监控管道（成功场景）
                await monitor_pipeline.execute(context)
                
                return result
                
            except Exception as exc:
                # 计算执行时间
                context.duration = time.time() - start_time
                context.exception = exc
                
                # 执行监控管道（错误场景）
                await monitor_pipeline.execute(context)
                
                raise
        
        return wrapper
    
    return decorator


def get_call_count(func_name: str) -> int:
    """获取方法的调用次数。
    
    Args:
        func_name: 方法全名（格式：module.ClassName.method_name）
    
    Returns:
        int: 调用次数
    """
    return _global_call_counter.get_count(func_name)


def reset_call_counters() -> None:
    """重置所有调用计数器。"""
    _global_call_counter.reset()


__all__ = [
    "CallCounterComponent",
    "ErrorReporterComponent",
    "MonitorComponent",
    "MonitorContext",
    "MonitorPipeline",
    "MonitorPipelineBuilder",
    "PrometheusMetricsReporterComponent",
    "SlowMethodDetectorComponent",
    "StandardMetricsReporterComponent",
    "get_call_count",
    "monitor",
    "reset_call_counters",
]

