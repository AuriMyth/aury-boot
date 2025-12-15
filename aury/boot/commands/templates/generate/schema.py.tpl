"""{class_name} Pydantic 模型。"""

{imports_str}from pydantic import BaseModel, ConfigDict, Field


class {class_name}Base(BaseModel):
    """{class_name} 基础模型。"""

{base_fields_str}


class {class_name}Create({class_name}Base):
    """创建 {class_name} 请求。"""

    pass


class {class_name}Update(BaseModel):
    """更新 {class_name} 请求。"""

{update_fields_str}


class {class_name}Response({class_name}Base):
    """{class_name} 响应。"""

{response_extra}

    model_config = ConfigDict(from_attributes=True)
