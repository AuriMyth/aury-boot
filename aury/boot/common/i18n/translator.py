"""翻译器。

提供多语言翻译和本地化功能。
"""

from __future__ import annotations

from datetime import datetime
import os
from typing import Any

from babel import Locale, dates, numbers
from babel.support import Format

from aury.boot.common.logging import logger

# 全局语言环境
_current_locale: str | None = None

# 翻译字典（由用户提供，框架不提供默认翻译）
_translations: dict[str, dict[str, str]] = {}


def get_locale() -> str:
    """获取当前语言环境。
    
    Returns:
        str: 当前语言环境代码（如 "zh_CN"）
    """
    global _current_locale
    if _current_locale is None:
        # 从环境变量获取，默认为中文
        _current_locale = os.getenv("LANG", "zh_CN").split(".")[0] or "zh_CN"
    return _current_locale


def set_locale(locale: str) -> None:
    """设置当前语言环境。
    
    Args:
        locale: 语言环境代码（如 "zh_CN", "en_US"）
    """
    global _current_locale
    _current_locale = locale
    logger.debug(f"语言环境已设置为: {locale}")


class Translator:
    """翻译器。
    
    提供多语言翻译和本地化功能。
    
    注意：框架不提供默认翻译字典，用户需要自行加载翻译资源。
    
    使用示例:
        # 加载翻译字典
        from aury.boot.common.i18n.translator import Translator, load_translations
        
        load_translations({
            "zh_CN": {
                "user.created": "用户 {name} 创建成功",
                "welcome": "欢迎",
            },
            "en_US": {
                "user.created": "User {name} created successfully",
                "welcome": "Welcome",
            },
        })
        
        # 使用翻译器
        translator = Translator(locale="zh_CN")
        message = translator.translate("user.created", name="张三")
        # "用户 张三 创建成功"
        
        # 日期本地化
        date_str = translator.format_date(datetime.now())
        
        # 数字本地化
        number_str = translator.format_number(1234.56)
    """
    
    def __init__(self, locale: str | None = None) -> None:
        """初始化翻译器。
        
        Args:
            locale: 语言环境代码（如 "zh_CN"），如果为 None 则使用全局设置
        """
        self._locale_str = locale or get_locale()
        try:
            self._locale = Locale.parse(self._locale_str)
        except Exception:
            # 如果解析失败，使用默认值
            logger.warning(f"无法解析语言环境 {self._locale_str}，使用默认值 zh_CN")
            self._locale = Locale.parse("zh_CN")
            self._locale_str = "zh_CN"
        
        self._formatter = Format(self._locale)
        logger.debug(f"翻译器已初始化: {self._locale_str}")
    
    @property
    def locale(self) -> str:
        """获取语言环境代码。"""
        return self._locale_str
    
    def translate(self, key: str, default: str | None = None, **kwargs: Any) -> str:
        """翻译文本。
        
        Args:
            key: 翻译键
            default: 默认值（如果找不到翻译）
            **kwargs: 格式化参数
            
        Returns:
            str: 翻译后的文本
        """
        translations = _translations.get(self._locale_str, {})
        template = translations.get(key, default)
        
        if template is None:
            logger.warning(f"翻译键未找到: {key} (locale: {self._locale_str})")
            return key
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"翻译格式化失败: {key}, 缺少参数: {e}")
            return template
    
    def format_date(
        self,
        date: datetime,
        format: str = "medium",
        timezone: str | None = None,
    ) -> str:
        """格式化日期。
        
        Args:
            date: 日期时间对象
            format: 格式（"short", "medium", "long", "full" 或自定义格式）
            timezone: 时区（可选）
            
        Returns:
            str: 格式化后的日期字符串
        """
        try:
            if format in ("short", "medium", "long", "full"):
                return dates.format_date(date, format=format, locale=self._locale)
            else:
                return dates.format_date(date, format=format, locale=self._locale)
        except Exception as e:
            logger.error(f"日期格式化失败: {e}")
            return str(date)
    
    def format_datetime(
        self,
        dt: datetime,
        format: str = "medium",
        timezone: str | None = None,
    ) -> str:
        """格式化日期时间。
        
        Args:
            dt: 日期时间对象
            format: 格式（"short", "medium", "long", "full" 或自定义格式）
            timezone: 时区（可选）
            
        Returns:
            str: 格式化后的日期时间字符串
        """
        try:
            if format in ("short", "medium", "long", "full"):
                return dates.format_datetime(dt, format=format, locale=self._locale)
            else:
                return dates.format_datetime(dt, format=format, locale=self._locale)
        except Exception as e:
            logger.error(f"日期时间格式化失败: {e}")
            return str(dt)
    
    def format_number(self, number: float, format: str | None = None) -> str:
        """格式化数字。
        
        Args:
            number: 数字
            format: 格式（可选，如 "#,##0.00"）
            
        Returns:
            str: 格式化后的数字字符串
        """
        try:
            if format:
                return numbers.format_number(number, format=format, locale=self._locale)
            else:
                return numbers.format_number(number, locale=self._locale)
        except Exception as e:
            logger.error(f"数字格式化失败: {e}")
            return str(number)
    
    def format_currency(self, amount: float, currency: str = "CNY") -> str:
        """格式化货币。
        
        Args:
            amount: 金额
            currency: 货币代码（如 "CNY", "USD"）
            
        Returns:
            str: 格式化后的货币字符串
        """
        try:
            return numbers.format_currency(amount, currency, locale=self._locale)
        except Exception as e:
            logger.error(f"货币格式化失败: {e}")
            return f"{currency} {amount}"


def load_translations(translations: dict[str, dict[str, str]]) -> None:
    """加载翻译字典。
    
    此函数用于加载用户提供的翻译资源。框架本身不提供默认翻译。
    
    Args:
        translations: 翻译字典，格式为 {locale: {key: message}}
        
    使用示例:
        load_translations({
            "zh_CN": {
                "user.created": "用户 {name} 创建成功",
                "welcome": "欢迎",
            },
            "en_US": {
                "user.created": "User {name} created successfully",
                "welcome": "Welcome",
            },
        })
    """
    global _translations
    _translations = translations
    logger.info(f"翻译字典已加载，支持语言: {', '.join(translations.keys())}")


def translate(key: str, default: str | None = None, locale: str | None = None, **kwargs: Any) -> str:
    """翻译文本（便捷函数）。
    
    Args:
        key: 翻译键
        default: 默认值
        locale: 语言环境（可选，默认使用全局设置）
        **kwargs: 格式化参数
        
    Returns:
        str: 翻译后的文本
    """
    translator = Translator(locale=locale)
    return translator.translate(key, default=default, **kwargs)


# 装饰器支持
def translate_decorator(locale: str | None = None):
    """翻译装饰器。
    
    使用示例:
        @translate_decorator("zh_CN")
        def get_message():
            return _("Welcome")  # 会被翻译
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, str):
                return translate(result, locale=locale)
            return result
        return wrapper
    return decorator
