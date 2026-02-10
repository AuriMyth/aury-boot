"""Aury 命名空间包（pkgutil namespace）。

`aury` 顶层命名空间可能同时由多个分发包提供（例如 `aury-sdk-storage`、`aury-boot`）。
为了避免其中任意一个分发包提供 `aury/__init__.py` 后把 `aury` 变成"普通包"
（从而阻止其它 sys.path 上的 `aury.*` 子包被发现），这里显式使用
`pkgutil.extend_path` 将其转换为"pkgutil 命名空间包"，允许多分发共存。
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
