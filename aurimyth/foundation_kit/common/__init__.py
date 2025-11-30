"""Common 层模块。

最基础层，提供：
- 异常基类
- 日志系统
- 国际化（i18n）
"""

from .exceptions import FoundationError
from .i18n import Translator, get_locale, load_translations, set_locale, translate
from .logging import (
    get_class_logger,
    log_exceptions,
    log_performance,
    logger,
    setup_logging,
)

__all__ = [
    # 异常
    "FoundationError",
    # 国际化
    "Translator",
    "get_class_logger",
    "get_locale",
    "load_translations",
    "log_exceptions",
    "log_performance",
    # 日志
    "logger",
    "set_locale",
    "setup_logging",
    "translate",
]

