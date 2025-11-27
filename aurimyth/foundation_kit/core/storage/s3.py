"""S3 存储实现。"""

import asyncio
from typing import list

import aioboto3
from botocore.config import Config

from .base import StorageClient, StorageConfig, StorageFile


class S3Client(StorageClient):
    def __init__(self, config: StorageConfig) -> None:
        self.access_key_id = config.access_key_id
        self.access_key_secret = config.access_key_secret
        self.endpoint = config.endpoint
        self.region = config.region

    async def _client(self):
        session = aioboto3.Session()
        return session.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.access_key_secret,
            endpoint_url=self.endpoint,
            region_name=self.region or None,
            config=Config(s3={"addressing_style": "virtual", "signature_version": "s3v4"}),
        )

    async def upload_file(self, file: StorageFile) -> str:
        async with await self._client() as client:
            await client.put_object(Bucket=file.bucket_name, Key=file.object_name, Body=file.data)
            return f"{self.endpoint}/{file.bucket_name}/{file.object_name}"

    async def upload_files(self, files: list[StorageFile]) -> list[str]:
        return await asyncio.gather(*(self.upload_file(file) for file in files))

    async def delete_file(self, file: StorageFile) -> None:
        async with await self._client() as client:
            await client.delete_object(Bucket=file.bucket_name, Key=file.object_name)


