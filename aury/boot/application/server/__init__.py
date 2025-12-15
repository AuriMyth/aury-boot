"""ASGI 服务器管理。

提供 uvicorn 服务器的完整集成。

包含：
- ApplicationServer 类：服务器管理
- run_app 函数：快速启动
"""

from __future__ import annotations

import os
import signal
import sys
from typing import TYPE_CHECKING, Any

from aury.boot.common.logging import logger

if TYPE_CHECKING:
    from aury.boot.application.app.base import FoundationApp


class ApplicationServer:
    """ASGI 应用服务器。
    
    基于 uvicorn，提供完整的服务器管理功能。
    
    使用示例:
        app = FoundationApp()
        server = ApplicationServer(
            app=app,
            host="0.0.0.0",
            port=8000,
            workers=4,
        )
        server.run()
    """
    
    def __init__(
        self,
        app: FoundationApp,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
        workers: int = 1,
        reload: bool = False,
        reload_dirs: list[str] | None = None,
        loop: str = "auto",
        http: str = "auto",
        interface: str = "auto",
        debug: bool = False,
        access_log: bool = True,
        use_colors: bool | None = None,
        log_config: dict | None = None,
        ssl_keyfile: str | None = None,
        ssl_certfile: str | None = None,
        ssl_keyfile_password: str | None = None,
        ssl_version: int | None = None,
        ssl_cert_reqs: int | None = None,
        ssl_ca_certs: str | None = None,
        ssl_ciphers: str | None = None,
        **kwargs,
    ) -> None:
        """初始化服务器。
        
        Args:
            app: FastAPI/FoundationApp 应用实例
            host: 监听地址，默认 127.0.0.1
            port: 监听端口，默认 8000
            workers: 工作进程数，默认 1
            reload: 是否启用热重载
            reload_dirs: 热重载监控目录
            loop: 事件循环实现 (auto/asyncio/uvloop)
            http: HTTP 协议版本 (auto/h11/httptools)
            interface: ASGI 接口版本 (auto/asgi3/asgi2)
            debug: 是否启用调试模式
            access_log: 是否记录访问日志
            use_colors: 是否使用彩色输出
            log_config: 自定义日志配置
            ssl_keyfile: SSL 密钥文件路径
            ssl_certfile: SSL 证书文件路径
            ssl_keyfile_password: SSL 密钥密码
            ssl_version: SSL 版本
            ssl_cert_reqs: SSL 证书请求模式
            ssl_ca_certs: SSL CA 证书文件
            ssl_ciphers: SSL 密码套件
            **kwargs: 传递给 uvicorn.Config 的其他参数
        """
        self.app = app
        self.host = host
        self.port = port
        self.workers = workers
        self.reload = reload
        self.reload_dirs = reload_dirs
        self.loop = loop
        self.http = http
        self.interface = interface
        self.debug = debug
        self.access_log = access_log
        self.use_colors = use_colors
        self.log_config = log_config or self._get_default_log_config()
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile_password = ssl_keyfile_password
        self.ssl_version = ssl_version
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs
        self.ssl_ciphers = ssl_ciphers
        self.extra_kwargs = kwargs
        
        self.server: Any = None
    
    def _get_default_log_config(self) -> dict:
        """获取默认日志配置。
        
        整合 uvicorn 日志和框架日志。
        """
        import uvicorn
        from uvicorn.config import LOGGING_CONFIG
        
        config = LOGGING_CONFIG.copy()
        
        # 调整日志格式
        config["formatters"]["access"]["format"] = (
            "%(asctime)s | %(client_addr)s - "
            "%(request_line)s | %(status_code)s"
        )
        config["formatters"]["default"]["format"] = (
            "%(asctime)s | %(levelname)s | %(name)s - %(message)s"
        )
        
        return config
    
    def get_config(self) -> Any:
        """获取 uvicorn 配置对象。
        
        Returns:
            uvicorn.Config: 服务器配置
        """
        import uvicorn
        
        # 从 uvicorn 0.30.0 开始，Config.__init__ 不再接受 ``debug`` 参数，
        # 这里仅在日志中使用 debug 标志，而不再传递给 uvicorn.Config，
        # 以避免 "unexpected keyword argument 'debug'" 异常。
        return uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            workers=self.workers,
            reload=self.reload,
            reload_dirs=self.reload_dirs,
            loop=self.loop,
            http=self.http,
            interface=self.interface,
            access_log=self.access_log,
            use_colors=self.use_colors,
            log_config=self.log_config,
            ssl_keyfile=self.ssl_keyfile,
            ssl_certfile=self.ssl_certfile,
            ssl_keyfile_password=self.ssl_keyfile_password,
            ssl_version=self.ssl_version,
            ssl_cert_reqs=self.ssl_cert_reqs,
            ssl_ca_certs=self.ssl_ca_certs,
            ssl_ciphers=self.ssl_ciphers,
            **self.extra_kwargs,
        )
    
    def run(self) -> None:
        """运行服务器。
        
        阻塞调用，服务器会一直运行直到收到中断信号。
        """
        import uvicorn
        
        config = self.get_config()
        self.server = uvicorn.Server(config)
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        # 记录启动信息
        self._log_startup_info()
        
        # 运行服务器
        try:
            self.server.run()
        except KeyboardInterrupt:
            logger.info("服务器已停止（Ctrl+C）")
        except Exception as exc:
            logger.error(f"服务器错误: {exc}", exc_info=True)
            sys.exit(1)
    
    async def run_async(self) -> None:
        """异步运行服务器。
        
        使用示例:
            server = ApplicationServer(app)
            await server.run_async()
        """
        import uvicorn
        
        config = self.get_config()
        self.server = uvicorn.Server(config)
        
        # 记录启动信息
        self._log_startup_info()
        
        # 运行服务器
        try:
            await self.server.serve()
        except KeyboardInterrupt:
            logger.info("服务器已停止")
        except Exception as exc:
            logger.error(f"服务器错误: {exc}", exc_info=True)
            sys.exit(1)
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器。
        
        处理 SIGTERM 和 SIGINT 信号，确保优雅关闭。
        """
        def handle_signal(signum, frame):
            logger.info(f"收到信号 {signum}，正在关闭...")
            if self.server:
                self.server.should_exit = True
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    
    def _log_startup_info(self) -> None:
        """记录启动信息。"""
        protocol = "https" if self.ssl_certfile else "http"
        url = f"{protocol}://{self.host}:{self.port}"
        
        logger.info(
            f"服务器启动 | "
            f"地址: {url} | "
            f"工作进程: {self.workers} | "
            f"热重载: {self.reload}"
        )
        
        if self.debug:
            logger.warning("调试模式已启用")
        
        if self.reload:
            default_dirs = [os.getcwd()] if not self.reload_dirs else self.reload_dirs
            logger.info(f"热重载监控目录: {default_dirs}")


def run_app(
    app: FoundationApp,
    *,
    host: str | None = None,
    port: int | None = None,
    workers: int | None = None,
    reload: bool = False,
    **kwargs,
) -> None:
    """快速运行应用。
    
    从环境变量或参数读取配置。
    
    使用示例:
        from aury.boot.application.server import run_app
        
        app = FoundationApp()
        run_app(app)
    
    环境变量支持:
        SERVER_HOST: 监听地址
        SERVER_PORT: 监听端口
        SERVER_WORKERS: 工作进程数
        SERVER_RELOAD: 是否热重载
    """
    # 从环境变量读取默认值
    host = host or os.getenv("SERVER_HOST", "127.0.0.1")
    port = port or int(os.getenv("SERVER_PORT", "8000"))
    workers = workers or int(os.getenv("SERVER_WORKERS", "1"))
    reload = reload or os.getenv("SERVER_RELOAD", "").lower() in ("true", "1", "yes")
    
    server = ApplicationServer(
        app=app,
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        **kwargs,
    )
    server.run()


__all__ = [
    "ApplicationServer",
    "run_app",
]

