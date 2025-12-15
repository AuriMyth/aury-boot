"""测试数据工厂。

提供便捷的测试数据生成工具，类似 Django 的 Factory。
"""

from __future__ import annotations

from typing import Any, TypeVar

from faker import Faker

from aury.boot.common.logging import logger
from aury.boot.domain.models import Base

ModelType = TypeVar("ModelType", bound=Base)

# 全局 Faker 实例
_faker = Faker(["zh_CN", "en_US"])


class Factory:
    """测试数据工厂。
    
    提供便捷的测试数据生成工具。
    
    使用示例:
        # 创建工厂
        user_factory = Factory(User)
        
        # 创建单个实例
        user = await user_factory.create(name="张三", email="zhangsan@example.com")
        
        # 创建多个实例
        users = await user_factory.create_batch(5, name="批量用户")
        
        # 使用 Faker 生成随机数据
        user = await user_factory.create()  # 使用默认值或随机生成
    """
    
    def __init__(self, model_class: type[ModelType], **defaults: Any) -> None:
        """初始化工厂。
        
        Args:
            model_class: 模型类
            **defaults: 默认属性值
        """
        self._model_class = model_class
        self._defaults = defaults
        logger.debug(f"创建工厂: {model_class.__name__}")
    
    def _generate_field_value(self, field_name: str, field_type: Any) -> Any:
        """生成字段值。
        
        Args:
            field_name: 字段名
            field_type: 字段类型
            
        Returns:
            Any: 生成的字段值
        """
        # 根据字段名和类型生成合适的值
        if "email" in field_name.lower():
            return _faker.email()
        elif "name" in field_name.lower() or "username" in field_name.lower():
            return _faker.name()
        elif "phone" in field_name.lower() or "mobile" in field_name.lower():
            return _faker.phone_number()
        elif "address" in field_name.lower():
            return _faker.address()
        elif "url" in field_name.lower():
            return _faker.url()
        elif "text" in field_name.lower() or "content" in field_name.lower():
            return _faker.text()
        elif "date" in field_name.lower() or "time" in field_name.lower():
            return _faker.date_time()
        elif "int" in str(field_type).lower() or "integer" in str(field_type).lower():
            return _faker.random_int()
        elif "float" in str(field_type).lower():
            return _faker.pyfloat()
        elif "bool" in str(field_type).lower() or "boolean" in str(field_type).lower():
            return _faker.boolean()
        else:
            return _faker.word()
    
    def _build_attributes(self, **overrides: Any) -> dict[str, Any]:
        """构建属性字典。
        
        Args:
            **overrides: 覆盖的属性值
            
        Returns:
            dict[str, Any]: 属性字典
        """
        attrs = self._defaults.copy()
        
        # 如果模型有字段定义，尝试生成缺失的字段
        if hasattr(self._model_class, "__table__"):
            table = self._model_class.__table__
            for column in table.columns:
                if column.name not in attrs and column.name not in overrides:
                    # 跳过主键和自动生成的字段
                    if column.primary_key or column.server_default:
                        continue
                    # 尝试生成值
                    attrs[column.name] = self._generate_field_value(column.name, column.type)
        
        # 应用覆盖值
        attrs.update(overrides)
        return attrs
    
    async def create(self, **kwargs: Any) -> ModelType:
        """创建单个实例。
        
        Args:
            **kwargs: 属性值（覆盖默认值）
            
        Returns:
            ModelType: 创建的模型实例
        """
        attrs = self._build_attributes(**kwargs)
        instance = self._model_class(**attrs)
        logger.debug(f"创建测试数据: {self._model_class.__name__}")
        return instance
    
    async def create_batch(self, size: int, **kwargs: Any) -> list[ModelType]:
        """批量创建实例。
        
        Args:
            size: 创建数量
            **kwargs: 属性值（覆盖默认值）
            
        Returns:
            list[ModelType]: 创建的模型实例列表
        """
        instances = []
        for _ in range(size):
            instance = await self.create(**kwargs)
            instances.append(instance)
        logger.debug(f"批量创建 {size} 个测试数据: {self._model_class.__name__}")
        return instances
    
    def build(self, **kwargs: Any) -> ModelType:
        """构建实例（不保存到数据库）。
        
        Args:
            **kwargs: 属性值（覆盖默认值）
            
        Returns:
            ModelType: 构建的模型实例
        """
        attrs = self._build_attributes(**kwargs)
        instance = self._model_class(**attrs)
        logger.debug(f"构建测试数据（未保存）: {self._model_class.__name__}")
        return instance
