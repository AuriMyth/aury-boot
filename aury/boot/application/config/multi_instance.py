"""多实例配置解析工具。

支持从环境变量解析 {PREFIX}_{INSTANCE}_{FIELD} 格式的多实例配置。

示例:
    DATABASE_DEFAULT_URL=postgresql://main...
    DATABASE_DEFAULT_POOL_SIZE=10
    DATABASE_ANALYTICS_URL=postgresql://analytics...
    
    解析后:
    {
        "default": {"url": "postgresql://main...", "pool_size": 10},
        "analytics": {"url": "postgresql://analytics..."}
    }
"""

from __future__ import annotations

import os
import re
from typing import Any

from pydantic import BaseModel


def parse_multi_instance_env(
    prefix: str,
    fields: list[str],
    *,
    type_hints: dict[str, type] | None = None,
) -> dict[str, dict[str, Any]]:
    """从环境变量解析多实例配置。
    
    Args:
        prefix: 环境变量前缀，如 "DATABASE"
        fields: 支持的字段列表，如 ["url", "pool_size", "echo"]
        type_hints: 字段类型提示，用于类型转换
        
    Returns:
        dict[str, dict[str, Any]]: 实例名 -> 配置字典
        
    示例:
        >>> parse_multi_instance_env("DATABASE", ["url", "pool_size"])
        {
            "default": {"url": "postgresql://...", "pool_size": "10"},
            "analytics": {"url": "postgresql://..."}
        }
    """
    instances: dict[str, dict[str, Any]] = {}
    type_hints = type_hints or {}
    
    # 构建正则：{PREFIX}_{INSTANCE}_{FIELD}
    # INSTANCE 和 FIELD 都是大写字母和下划线
    fields_pattern = "|".join(re.escape(f.upper()) for f in fields)
    pattern = re.compile(
        rf"^{prefix}_([A-Z][A-Z0-9_]*)_({fields_pattern})$",
        re.IGNORECASE
    )
    
    for key, value in os.environ.items():
        match = pattern.match(key)
        if match:
            instance_name = match.group(1).lower()
            field_name = match.group(2).lower()
            
            # 类型转换
            converted_value = _convert_value(value, type_hints.get(field_name))
            
            if instance_name not in instances:
                instances[instance_name] = {}
            instances[instance_name][field_name] = converted_value
    
    return instances


def _convert_value(value: str, target_type: type | None) -> Any:
    """转换环境变量值到目标类型。"""
    if target_type is None:
        return value
    
    if target_type is bool:
        return value.lower() in ("true", "1", "yes", "on")
    elif target_type is int:
        return int(value)
    elif target_type is float:
        return float(value)
    elif target_type is list:
        # 简单的逗号分隔
        return [v.strip() for v in value.split(",") if v.strip()]
    else:
        return value


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
        hints = {}
        for name, field_info in cls.model_fields.items():
            annotation = field_info.annotation
            # 处理 Optional 类型
            if hasattr(annotation, "__origin__"):
                # 如 str | None -> str
                args = getattr(annotation, "__args__", ())
                for arg in args:
                    if arg is not type(None):
                        hints[name] = arg
                        break
            else:
                hints[name] = annotation
        return hints


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
