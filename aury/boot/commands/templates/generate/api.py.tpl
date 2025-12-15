"""{class_name} API 路由。"""

{uuid_import}from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.application.interfaces.egress import (
    BaseResponse,
    Pagination,
    PaginationResponse,
)
from aury.boot.infrastructure.database import DatabaseManager

from {import_prefix}schemas.{file_name} import (
    {class_name}Create,
    {class_name}Response,
    {class_name}Update,
)
from {import_prefix}services.{file_name}_service import {class_name}Service

router = APIRouter(prefix="/v1/{var_name_plural}", tags=["{class_name}"])
db_manager = DatabaseManager.get_instance()


async def get_service(
    session: AsyncSession = Depends(db_manager.get_session),
) -> {class_name}Service:
    """获取服务实例。"""
    return {class_name}Service(session)


@router.get("", response_model=PaginationResponse[{class_name}Response])
async def list_{var_name_plural}(
    skip: int = 0,
    limit: int = 20,
    service: {class_name}Service = Depends(get_service),
) -> PaginationResponse[{class_name}Response]:
    """获取 {class_name} 列表。"""
    items = await service.list(skip=skip, limit=limit)
    return PaginationResponse(
        code=200,
        message="获取成功",
        data=Pagination(
            total=len(items),
            items=[{class_name}Response.model_validate(item) for item in items],
            page=skip // limit + 1,
            size=limit,
        ),
    )


@router.get("/{{id}}", response_model=BaseResponse[{class_name}Response])
async def get_{var_name}(
    id: {id_type},
    service: {class_name}Service = Depends(get_service),
) -> BaseResponse[{class_name}Response]:
    """获取 {class_name} 详情。"""
    entity = await service.get(id)
    return BaseResponse(
        code=200,
        message="获取成功",
        data={class_name}Response.model_validate(entity),
    )


@router.post("", response_model=BaseResponse[{class_name}Response])
async def create_{var_name}(
    data: {class_name}Create,
    service: {class_name}Service = Depends(get_service),
) -> BaseResponse[{class_name}Response]:
    """创建 {class_name}。"""
    entity = await service.create(data)
    return BaseResponse(
        code=200,
        message="创建成功",
        data={class_name}Response.model_validate(entity),
    )


@router.put("/{{id}}", response_model=BaseResponse[{class_name}Response])
async def update_{var_name}(
    id: {id_type},
    data: {class_name}Update,
    service: {class_name}Service = Depends(get_service),
) -> BaseResponse[{class_name}Response]:
    """更新 {class_name}。"""
    entity = await service.update(id, data)
    return BaseResponse(
        code=200,
        message="更新成功",
        data={class_name}Response.model_validate(entity),
    )


@router.delete("/{{id}}", response_model=BaseResponse[None])
async def delete_{var_name}(
    id: {id_type},
    service: {class_name}Service = Depends(get_service),
) -> BaseResponse[None]:
    """删除 {class_name}。"""
    await service.delete(id)
    return BaseResponse(
        code=200,
        message="删除成功",
        data=None,
    )
