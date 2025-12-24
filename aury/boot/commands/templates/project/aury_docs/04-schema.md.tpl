# Schema（Pydantic 模型）

## 4.1 Schema 编写示例

**文件**: `{package_name}/schemas/user.py`

```python
"""User Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class UserBase(BaseModel):
    """User 基础模型。"""
    name: str = Field(..., min_length=1, max_length=100, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    is_active: bool = Field(default=True, description="是否激活")


class UserCreate(UserBase):
    """创建 User 请求。"""
    password: str = Field(..., min_length=6, description="密码")


class UserUpdate(BaseModel):
    """更新 User 请求（所有字段可选）。"""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """User 响应。"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## 4.2 Schema 使用说明

Schema（Pydantic 模型）在框架中扮演三个角色：

1. **请求验证**：验证 API 请求数据（Create/Update）
2. **响应序列化**：将 ORM 模型转换为 JSON 响应（Response）
3. **类型提示**：为 Service 层提供类型安全

**数据流转**：
```
API 请求 → Schema 验证 → Service 处理 → Repository 操作 → ORM Model
                ↓                                              ↓
          model_dump()                            model_validate()
                                                               ↓
                                                      Response Schema → JSON 响应
```

**关键方法**：
- `model_dump()`：将 Schema 转为字典（传给 Repository）
- `model_dump(exclude_unset=True)`：只转换设置过的字段（用于更新）
- `model_validate(orm_obj)`：从 ORM 模型创建 Schema（需要 `from_attributes=True`）

> **重要提示**：不要自定义通用响应 Schema（如 `OkResponse`、`ErrorResponse`）。
> 框架已内置 `BaseResponse` 和 `PaginationResponse`，直接使用即可。
> 异常响应由全局异常处理中间件自动处理，无需手动定义。

## 4.3 常用验证

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class ExampleSchema(BaseModel):
    # 长度限制
    name: str = Field(..., min_length=1, max_length=100)
    
    # 数值范围
    age: int = Field(..., ge=0, le=150)
    price: float = Field(..., gt=0)
    
    # 正则验证
    phone: str = Field(..., pattern=r"^1[3-9]\d{{9}}$")
    
    # 枚举
    status: Literal["active", "inactive", "pending"]
    
    # 字段验证器
    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        return v.strip()
```
