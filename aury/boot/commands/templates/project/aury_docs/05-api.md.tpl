# API（路由层）

## 5.1 API 编写示例

**文件**: `{package_name}/api/user.py`

```python
"""User API 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.application.interfaces.egress import (
    BaseResponse,
    Pagination,
    PaginationResponse,
)
from aury.boot.infrastructure.database import DatabaseManager

from {package_name}.schemas.user import UserCreate, UserResponse, UserUpdate
from {package_name}.services.user_service import UserService

router = APIRouter(prefix="/v1/users", tags=["User"])
db_manager = DatabaseManager.get_instance()


async def get_service(
    session: AsyncSession = Depends(db_manager.get_session),
) -> UserService:
    return UserService(session)


@router.get("", response_model=PaginationResponse[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    service: UserService = Depends(get_service),
) -> PaginationResponse[UserResponse]:
    """获取列表。"""
    items = await service.list(skip=skip, limit=limit)
    return PaginationResponse(
        code=200,
        message="获取成功",
        data=Pagination(
            total=len(items),
            items=[UserResponse.model_validate(item) for item in items],
            page=skip // limit + 1,
            size=limit,
        ),
    )


@router.get("/{{id}}", response_model=BaseResponse[UserResponse])
async def get_user(
    id: UUID,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """获取详情。"""
    entity = await service.get(id)
    return BaseResponse(
        code=200,
        message="获取成功",
        data=UserResponse.model_validate(entity),
    )


@router.post("", response_model=BaseResponse[UserResponse])
async def create_user(
    data: UserCreate,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """创建。"""
    entity = await service.create(data)
    return BaseResponse(
        code=200,
        message="创建成功",
        data=UserResponse.model_validate(entity),
    )


@router.put("/{{id}}", response_model=BaseResponse[UserResponse])
async def update_user(
    id: UUID,
    data: UserUpdate,
    service: UserService = Depends(get_service),
) -> BaseResponse[UserResponse]:
    """更新。"""
    entity = await service.update(id, data)
    return BaseResponse(
        code=200,
        message="更新成功",
        data=UserResponse.model_validate(entity),
    )


@router.delete("/{{id}}", response_model=BaseResponse[None])
async def delete_user(
    id: UUID,
    service: UserService = Depends(get_service),
) -> BaseResponse[None]:
    """删除。"""
    await service.delete(id)
    return BaseResponse(code=200, message="删除成功", data=None)
```

## 5.2 注册路由

```python
from fastapi import FastAPI
from {package_name}.api.user import router as user_router

app = FastAPI()
app.include_router(user_router)
```
