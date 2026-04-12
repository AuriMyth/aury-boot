"""多实例配置解析工具。

支持从环境变量解析 {PREFIX}__{INSTANCE}__{FIELD} 格式的多实例配置。
使用双下划线 (__) 作为层级分隔符，符合行业标准。

示例:
    DATABASE__DEFAULT__URL=postgresql://main...
    DATABASE__DEFAULT__POOL_SIZE=10
    DATABASE__ANALYTICS__URL=postgresql://analytics...
    
    解析后:
    {
        "default": {"url": "postgresql://main...", "pool_size": 10},
        "analytics": {"url": "postgresql://analytics..."}
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, get_args, get_origin

from pydantic import BaseModel


def parse_multi_instance_env(
    prefix: str,
    fields: list[str] | None = None,
    *,
    type_hints: dict[str, type] | None = None,
) -> dict[str, dict[str, Any]]:
    """从环境变量解析多实例配置。
    
    使用双下划线 (__) 作为层级分隔符：
    - {PREFIX}__{INSTANCE}__{FIELD}=value
    
    Args:
        prefix: 环境变量前缀，如 "DATABASE"
        fields: 支持的字段列表（可选，用于过滤）
        type_hints: 字段类型提示，用于类型转换
        
    Returns:
        dict[str, dict[str, Any]]: 实例名 -> 配置字典
        
    示例:
        >>> parse_multi_instance_env("DATABASE")
        {
            "default": {"url": "postgresql://...", "pool_size": 10},
            "analytics": {"url": "postgresql://..."}
        }
    """
    instances: dict[str, dict[str, Any]] = {}
    type_hints = type_hints or {}
    prefix_with_sep = f"{prefix}__"
    
    # 将 fields 转为大写集合用于过滤
    valid_fields: set[str] | None = None
    if fields:
        valid_fields = {f.upper() for f in fields}
    
    for key, value in os.environ.items():
        # 检查前缀
        if not key.upper().startswith(prefix_with_sep):
            continue
        
        # 移除前缀后分割
        remainder = key[len(prefix_with_sep):]
        parts = remainder.split("__")
        
        if len(parts) < 2:
            continue
        
        instance_name = parts[0].lower()
        field_path = [part.lower() for part in parts[1:]]
        top_level_field = parts[1].upper()
        
        # 如果指定了字段列表，进行过滤
        if valid_fields and top_level_field not in valid_fields:
            continue
        
        # 类型转换
        hint_key = ".".join(field_path)
        converted_value = _convert_value(
            value,
            type_hints.get(hint_key) or type_hints.get(field_path[0]),
        )
        
        if instance_name not in instances:
            instances[instance_name] = {}
        _assign_nested_value(instances[instance_name], field_path, converted_value)
    
    return instances


def _convert_value(value: str, target_type: type | None) -> Any:
    """转换环境变量值到目标类型。"""
    if target_type is None:
        return value

    origin = get_origin(target_type)
    if origin is not None:
        target_type = origin

    if target_type is bool:
        return value.lower() in ("true", "1", "yes", "on")
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type in {list, tuple, set}:
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = [item.strip() for item in text.split(",") if item.strip()]
        else:
            parsed = [item.strip() for item in text.replace("\n", ",").split(",") if item.strip()]
        return list(parsed)
    if target_type is dict:
        return json.loads(value)
    return value


def _assign_nested_value(target: dict[str, Any], path: list[str], value: Any) -> None:
    """按路径写入嵌套字典。"""
    current = target
    for key in path[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            next_value = {}
            current[key] = next_value
        current = next_value
    current[path[-1]] = value


class MultiInstanceSettings(BaseModel):
    """多实例配置基类。
    
    子类需要定义各实例共享的配置字段。
    """
    
    @classmethod
    def get_field_names(cls) -> list[str]:
        """获取所有字段名。"""
        return list(cls.model_fields.keys())
    
    @classmethod
    def get_type_hints(cls) -> dict[str, type]:
        """获取字段类型提示。"""
        return _collect_type_hints(cls)


def _collect_type_hints(
    model_class: type[BaseModel],
    *,
    prefix: str = "",
) -> dict[str, type]:
    """递归收集配置字段类型，支持嵌套 BaseModel。"""
    hints: dict[str, type] = {}

    for name, field_info in model_class.model_fields.items():
        annotation = _unwrap_optional(field_info.annotation)
        key = f"{prefix}.{name}" if prefix else name

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            hints.update(_collect_type_hints(annotation, prefix=key))
            continue

        hints[key] = annotation

    return hints


def _unwrap_optional(annotation: type | Any) -> type | Any:
    """提取 Optional[T] / T | None 中的实际类型。"""
    origin = get_origin(annotation)
    if origin is None:
        return annotation

    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


class MultiInstanceConfigLoader:
    """多实例配置加载器。
    
    使用示例:
        loader = MultiInstanceConfigLoader("DATABASE", DatabaseInstanceConfig)
        instances = loader.load()
        # {"default": DatabaseInstanceConfig(...), "analytics": DatabaseInstanceConfig(...)}
    """
    
    def __init__(
        self,
        prefix: str,
        config_class: type[MultiInstanceSettings],
    ):
        """初始化加载器。
        
        Args:
            prefix: 环境变量前缀
            config_class: 配置类（继承自 MultiInstanceSettings）
        """
        self.prefix = prefix.upper()
        self.config_class = config_class
    
    def load(self) -> dict[str, MultiInstanceSettings]:
        """加载所有实例配置。
        
        Returns:
            dict[str, config_class]: 实例名 -> 配置对象
        """
        fields = self.config_class.get_field_names()
        type_hints = self.config_class.get_type_hints()
        
        raw_instances = parse_multi_instance_env(
            self.prefix,
            fields,
            type_hints=type_hints,
        )
        
        # 转换为配置对象
        instances = {}
        for name, config_dict in raw_instances.items():
            try:
                instances[name] = self.config_class(**config_dict)
            except Exception as e:
                # 配置不完整时跳过，让 Pydantic 验证报错
                raise ValueError(
                    f"配置实例 [{self.prefix}_{name.upper()}] 无效: {e}"
                ) from e
        
        return instances
    
    def load_or_default(
        self,
        default_instance: str = "default",
    ) -> dict[str, MultiInstanceSettings]:
        """加载配置，如果没有任何实例则返回包含默认实例的字典。
        
        Args:
            default_instance: 默认实例名
            
        Returns:
            dict[str, config_class]: 实例名 -> 配置对象
        """
        instances = self.load()
        
        if not instances:
            # 没有配置任何实例，创建一个默认的
            instances[default_instance] = self.config_class()
        
        return instances


__all__ = [
    "MultiInstanceConfigLoader",
    "MultiInstanceSettings",
    "parse_multi_instance_env",
]
