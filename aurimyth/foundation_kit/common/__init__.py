"""Common 层模块。

最基础层，提供：
- 异常基类
- 日志系统
- 国际化（i18n）
"""

from .exceptions import FoundationError
from .i18n import Translator, get_locale, load_translations, set_locale, translate
from .logging import (
    LoggerMixin,
    log_exceptions,
    log_performance,
    logger,
    setup_logging,
)

__all__ = [
    # 异常
    "FoundationError",
    # 日志
    "logger",
    "setup_logging",
    "log_performance",
    "log_exceptions",
    "LoggerMixin",
    # 国际化
    "Translator",
    "translate",
    "get_locale",
    "set_locale",
    "load_translations",
]

