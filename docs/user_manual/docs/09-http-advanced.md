# 7. HTTP 接口 - 高级指南

## Ingress 和 Egress 概览

Kit 提供了两个核心的接口层：

- **Ingress**（入口）：所有 API 请求的基类模型
  - `BaseRequest`：基础请求
  - `PaginationRequest`：分页请求
  - `ListRequest`：列表请求
  - `FilterRequest`：过滤请求
  - `SortOrder`：排序方向枚举

- **Egress**（出口）：所有 API 响应的基类模型
  - `BaseResponse[T]`：通用响应
  - `PaginationResponse[T]`：分页响应
  - `SuccessResponse`：成功消息
  - `ErrorResponse`：错误响应
  - `IDResponse`：ID 响应
  - `CountResponse`：计数响应
  - `ResponseBuilder`：响应构建器

使用这些标准模型确保 API 的一致性和可预测性。

## 统一响应格式

Kit 提供了统一的响应模型，所有 API 返回都应该使用 `BaseResponse` 或其衍生类。

### BaseResponse 结构

```python
from aury.boot.application.interfaces.egress import BaseResponse
from datetime import datetime

# BaseResponse 包含以下字段：
{
    "code": 200,              # 响应状态码
    "message": "操作成功",    # 响应消息
    "data": {...},            # 响应数据（泛型）
    "timestamp": "2024-01-01T12:00:00Z"  # 响应时间戳
}
```

### 基本使用

```python
from fastapi import APIRouter
from aury.boot.application.interfaces.egress import BaseResponse

router = APIRouter()

# 返回单个对象
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.get_user(user_id)
    return BaseResponse(
        code=200,
        message="获取成功",
        data=user
    )

# 返回简单值
@router.get("/count")
async def get_count():
    count = await db.count_users()
    return BaseResponse(
        code=200,
        message="获取成功",
        data=count
    )

# 返回 None（不需要数据）
@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    await db.delete_user(user_id)
    return BaseResponse(
        code=200,
        message="删除成功",
        data=None
    )
```

## 分页响应

### Pagination 模型

```python
from aury.boot.application.interfaces.egress import (
    Pagination,
    PaginationResponse
)

# Pagination 包含：
{
    "total": 100,           # 总记录数
    "items": [...],         # 数据列表
    "page": 1,              # 当前页码（从 1 开始）
    "size": 20,             # 每页大小
    "pages": 5              # 总页数（自动计算）
}

# 附加属性：
pagination.has_next         # 是否有下一页
pagination.has_prev         # 是否有上一页
pagination.skip             # 跳过的记录数（用于 SQL OFFSET）
```

### 分页响应示例

```python
@router.get("/users")
async def list_users(
    page: int = 1,
    size: int = 20,
    repo=Depends(get_user_repo)
):
    # 获取分页数据
    items, total = await repo.paginate(page=page, size=size)
    
    # 构造 Pagination 对象
    pagination = Pagination(
        total=total,
        items=items,
        page=page,
        size=size
    )
    
    # 返回分页响应
    return PaginationResponse(
        code=200,
        message="获取列表成功",
        data=pagination
    )
```

## 特殊响应类型

### SuccessResponse - 简单成功消息

```python
from aury.boot.application.interfaces.egress import SuccessResponse

@router.post("/users")
async def create_user(request: UserCreateRequest):
    user = await service.create(request)
    
    # 使用工厂方法创建
    return SuccessResponse.create(
        message="用户创建成功",
        data={"user_id": user.id}
    )
```

### ErrorResponse - 错误响应

```python
from aury.boot.application.interfaces.egress import ErrorResponse

@router.post("/users")
async def create_user(request: UserCreateRequest):
    try:
        user = await service.create(request)
        return BaseResponse(code=200, message="成功", data=user)
    except EmailAlreadyExists:
        return ErrorResponse.create(
            code=400,
            message="邮箱已存在",
            error_code="EMAIL_DUPLICATE"
        )
```

### IDResponse - 返回 ID

```python
from aury.boot.application.interfaces.egress import IDResponse

@router.post("/users")
async def create_user(request: UserCreateRequest):
    user = await service.create(request)
    return IDResponse(
        code=200,
        message="用户创建成功",
        data=user.id  # 只返回 ID
    )
```

### CountResponse - 返回计数

```python
from aury.boot.application.interfaces.egress import CountResponse

@router.get("/users/count")
async def count_users():
    count = await repo.count()
    return CountResponse(
        code=200,
        message="获取成功",
        data=count
    )
```

## ResponseBuilder - 便捷构造器

### 使用 ResponseBuilder

```python
from aury.boot.application.interfaces.egress import ResponseBuilder

# 成功响应
return ResponseBuilder.success(
    message="操作成功",
    data={"key": "value"},
    code=200
)

# 失败响应
return ResponseBuilder.fail(
    message="操作失败",
    code=400,
    error_code="VALIDATION_ERROR",
    errors=[
        {"field": "email", "message": "邮箱格式不正确"}
    ]
)
```

## 请求模型 - Ingress

Kit 提供了内置的请求模型基类，方便构建标准的 API 请求：

### BaseRequest - 基础请求

```python
from aury.boot.application.interfaces.ingress import BaseRequest
from pydantic import Field

class UserCreateRequest(BaseRequest):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, description="密码")

# BaseRequest 自动包含：
# - request_id: str | None  # 请求追踪 ID
```

### PaginationRequest - 分页请求

```python
from aury.boot.application.interfaces.ingress import (
    PaginationRequest,
    SortOrder
)

class UserListRequest(PaginationRequest):
    """用户列表请求"""
    keyword: str | None = Field(None, description="搜索关键词")
    is_active: bool | None = Field(None, description="是否活跃")

# PaginationRequest 包含：
# - page: int = 1           # 页码（从 1 开始）
# - size: int = 20          # 每页数量
# - sort: str | None        # 排序字段
# - order: SortOrder        # 排序方向（asc/desc）
# - request_id: str | None  # 请求追踪 ID

# 自动提供属性：
pagination_req = UserListRequest(page=2, size=50)
pagination_req.skip        # 跳过的记录数（50）
pagination_req.limit       # 限制数量（50）
```

### ListRequest - 列表请求（不分页）

```python
from aury.boot.application.interfaces.ingress import ListRequest

class UserListAllRequest(ListRequest):
    """获取所有用户请求"""
    keyword: str | None = Field(None, description="搜索关键词")

# ListRequest 包含：
# - limit: int | None       # 限制返回数量（最多 1000）
# - offset: int = 0         # 偏移量
# - sort: str | None        # 排序字段
# - order: SortOrder        # 排序方向

list_req = UserListAllRequest(limit=100, offset=0)
# 使用 offset 处理数据库查询
items = await db.query(User).offset(list_req.offset).limit(list_req.limit).all()
```

### FilterRequest - 过滤请求

```python
from aury.boot.application.interfaces.ingress import FilterRequest

class UserFilterRequest(FilterRequest):
    """用户过滤请求"""
    keyword: str | None = Field(None, description="关键词")

# FilterRequest 包含：
# - filters: dict | None    # 过滤条件字典

filter_req = UserFilterRequest(filters={"status": "active", "role": "admin"})
# 使用 filters 动态构建查询条件
```

### 在路由中使用

```python
from fastapi import APIRouter
from aury.boot.application.interfaces.ingress import PaginationRequest

router = APIRouter()

# 方式 1：使用 Query 参数（自动解析）
@router.get("/users")
async def list_users(
    page: int = 1,
    size: int = 20,
    keyword: str | None = None,
    service=Depends(get_user_service)
):
    """获取用户列表"""
    items, total = await service.search(
        keyword=keyword,
        page=page,
        size=size
    )
    pagination = Pagination(
        total=total,
        items=items,
        page=page,
        size=size
    )
    return PaginationResponse(code=200, message="获取列表成功", data=pagination)

# 方式 2：使用请求模型（推荐用于复杂查询）
class UserSearchRequest(PaginationRequest):
    keyword: str | None = None
    is_active: bool | None = None

@router.post("/users/search")
async def search_users(
    request: UserSearchRequest,
    service=Depends(get_user_service)
):
    """搜索用户"""
    items, total = await service.search(
        keyword=request.keyword,
        is_active=request.is_active,
        page=request.page,
        size=request.size,
        sort=request.sort,
        order=request.order
    )
    pagination = Pagination(
        total=total,
        items=items,
        page=request.page,
        size=request.size
    )
    return PaginationResponse(code=200, message="搜索成功", data=pagination)
```

## 定义自定义请求模型

### 创建清晰的请求模型

```python
from pydantic import BaseModel, EmailStr, Field

class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, description="密码")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "secure_password_123"
            }
        }

class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = Field(None)
    bio: str | None = Field(None, max_length=500)
```

### 使用验证器

```python
from pydantic import BaseModel, field_validator

class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    password_confirm: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('密码至少 8 个字符')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含大写字母')
        return v
    
    @field_validator('password_confirm')
    @classmethod
    def validate_password_match(cls, v, info):
        if v != info.data.get('password'):
            raise ValueError('两次输入的密码不一致')
        return v
```

## 完整 CRUD 示例

```python
from fastapi import APIRouter, Depends, HTTPException
from aury.boot.application.interfaces.egress import (
    BaseResponse,
    PaginationResponse,
    Pagination,
)

router = APIRouter(prefix="/users", tags=["users"])

# CREATE
@router.post("")
async def create_user(
    request: UserCreateRequest,
    service=Depends(get_user_service)
):
    """创建用户"""
    try:
        user = await service.create(request)
        return BaseResponse(
            code=200,
            message="用户创建成功",
            data=user
        )
    except EmailAlreadyExists as e:
        raise HTTPException(status_code=400, detail=str(e))

# READ
@router.get("/{user_id}")
async def get_user(
    user_id: str,
    service=Depends(get_user_service)
):
    """获取单个用户"""
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return BaseResponse(
        code=200,
        message="获取成功",
        data=user
    )

# LIST
@router.get("")
async def list_users(
    page: int = 1,
    size: int = 20,
    service=Depends(get_user_service)
):
    """获取用户列表（分页）"""
    items, total = await service.list_users(page=page, size=size)
    pagination = Pagination(
        total=total,
        items=items,
        page=page,
        size=size
    )
    return PaginationResponse(
        code=200,
        message="获取列表成功",
        data=pagination
    )

# UPDATE
@router.put("/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    service=Depends(get_user_service)
):
    """更新用户"""
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user = await service.update_user(user_id, request)
    return BaseResponse(
        code=200,
        message="更新成功",
        data=user
    )

# DELETE
@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    service=Depends(get_user_service)
):
    """删除用户"""
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return BaseResponse(
        code=200,
        message="删除成功",
        data=None
    )
```

## 错误处理

### 异常与响应映射

```python
from fastapi import FastAPI
from aury.boot.application.errors import (
    NotFoundError,
    AlreadyExistsError,
    UnauthorizedError,
)
from aury.boot.application.interfaces.egress import ErrorResponse

app = FastAPI()

@app.exception_handler(NotFoundError)
async def not_found_handler(request, exc):
    return ErrorResponse.create(
        code=404,
        message=str(exc),
        error_code="NOT_FOUND"
    )

@app.exception_handler(AlreadyExistsError)
async def already_exists_handler(request, exc):
    return ErrorResponse.create(
        code=400,
        message=str(exc),
        error_code="ALREADY_EXISTS"
    )
```

### 验证错误处理

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": "请求参数验证失败",
            "error_code": "VALIDATION_ERROR",
            "details": {"errors": errors}
        }
    )
```

## 常见问题

### Q: 为什么不使用 FastAPI 的 response_model？

A: Kit 采用统一的响应格式有以下优势：
- 所有 API 响应结构一致
- 自动包含时间戳和状态码
- 便于客户端处理
- 支持国际化错误消息

### Q: 如何返回自定义数据结构？

A: 使用 `BaseResponse[T]` 的泛型：

```python
from aury.boot.application.interfaces.egress import BaseResponse
from pydantic import BaseModel

class CustomData(BaseModel):
    key1: str
    key2: int

return BaseResponse[CustomData](
    code=200,
    message="成功",
    data=CustomData(key1="value", key2=123)
)
```

### Q: 能否自定义响应字段？

A: 可以继承 `BaseResponse`：

```python
from aury.boot.application.interfaces.egress import BaseResponse
from pydantic import Field

class CustomResponse(BaseResponse[dict]):
    extra_field: str = Field(..., description="额外字段")

return CustomResponse(
    code=200,
    message="成功",
    data={},
    extra_field="custom_value"
)
```

## 下一步

- 查看 [08-error-handling-guide.md](./08-error-handling-guide.md) 了解错误处理
- 查看 [09-database-complete.md](./09-database-complete.md) 了解数据访问
- 查看 [20-best-practices.md](./20-best-practices.md) 了解最佳实践

