"""国际化模块。

提供多语言翻译、日期/数字本地化等功能。

注意：框架不提供默认翻译字典，用户需要调用 load_translations() 加载翻译资源。
"""

from .translator import Translator, get_locale, load_translations, set_locale, translate

__all__ = [
    "Translator",
    "get_locale",
    "load_translations",
    "set_locale",
    "translate",
]
