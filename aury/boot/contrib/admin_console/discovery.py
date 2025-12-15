from __future__ import annotations

import importlib
from typing import Any

from aury.boot.common.logging import logger


def _candidate_modules(app: Any, config: Any) -> list[str]:
    """生成项目侧 admin-console 模块候选列表（多策略自动发现）。

    参考 SchedulerComponent._autodiscover_schedules 的风格：
    - settings 显式指定优先
    - 读取 [tool.aury].package
    - service.name / 调用者模块推断
    - 最后尝试根模块 admin_console/admin
    """
    modules: list[str] = []

    # 策略 0：显式指定
    views_module = getattr(getattr(config, "admin", None), "views_module", None)
    if views_module:
        modules.append(str(views_module).strip())

    # 策略 1：读取 pyproject.toml 的 [tool.aury].package
    try:
        from aury.boot.commands.config import get_project_config

        cfg = get_project_config()
        if getattr(cfg, "has_package", False):
            pkg = cfg.package
            modules.extend([f"{pkg}.admin_console", f"{pkg}.admin"])
    except Exception:
        pass

    # 策略 2：service.name 推断
    service_name = (getattr(getattr(config, "service", None), "name", None) or "").strip()
    if service_name and service_name not in {"app", "main"}:
        modules.extend([f"{service_name}.admin_console", f"{service_name}.admin"])

    # 策略 3：从调用者模块推断
    caller = getattr(app, "_caller_module", "__main__")
    if caller in ("__main__", "main"):
        modules.extend(["admin_console", "admin"])
    elif "." in str(caller):
        package = str(caller).rsplit(".", 1)[0]
        modules.extend([f"{package}.admin_console", f"{package}.admin", "admin_console", "admin"])
    else:
        modules.extend([f"{caller}.admin_console", f"{caller}.admin", "admin_console", "admin"])

    # 去重，保持顺序
    seen: set[str] = set()
    return [m for m in modules if m and not (m in seen or seen.add(m))]


def load_project_admin_module(app: Any, config: Any):
    """尝试导入项目侧 admin-console 模块，成功则返回 module，否则返回 None。"""
    for module_name in _candidate_modules(app, config):
        try:
            module = importlib.import_module(module_name)
            logger.info(f"已加载管理后台模块: {module_name}")
            return module
        except ImportError:
            logger.debug(f"管理后台模块不存在: {module_name}")
        except Exception as exc:
            logger.warning(f"加载管理后台模块失败 ({module_name}): {exc}")
    return None


