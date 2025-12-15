"""{class_name} 业务逻辑层。"""

{uuid_import}from sqlalchemy.ext.asyncio import AsyncSession

from aury.boot.application.errors import AlreadyExistsError, NotFoundError
from aury.boot.domain.service.base import BaseService
from aury.boot.domain.transaction import transactional

from {import_prefix}models.{file_name} import {class_name}
from {import_prefix}repositories.{file_name}_repository import {class_name}Repository
from {import_prefix}schemas.{file_name} import {class_name}Create, {class_name}Update


class {class_name}Service(BaseService):
    """{class_name} 服务。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repo = {class_name}Repository(session, {class_name})

    async def get(self, id: {id_py_type}) -> {class_name}:
        """获取 {class_name}。"""
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"{class_name} 不存在", resource=id)
        return entity

    async def list(self, skip: int = 0, limit: int = 100) -> list[{class_name}]:
        """获取 {class_name} 列表。"""
        return await self.repo.list(skip=skip, limit=limit)

    @transactional
    async def create(self, data: {class_name}Create) -> {class_name}:
        """创建 {class_name}。"""
{unique_check_str}
        return await self.repo.create(data.model_dump())

    @transactional
    async def update(self, id: {id_py_type}, data: {class_name}Update) -> {class_name}:
        """更新 {class_name}。"""
        entity = await self.get(id)
        return await self.repo.update(entity, data.model_dump(exclude_unset=True))

    @transactional
    async def delete(self, id: {id_py_type}) -> None:
        """删除 {class_name}。"""
        entity = await self.get(id)
        await self.repo.delete(entity)
