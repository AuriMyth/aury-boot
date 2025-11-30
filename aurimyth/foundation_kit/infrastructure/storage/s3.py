"""S3 存储实现。

支持 AWS S3、MinIO 等兼容 S3 协议的对象存储服务。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.storage.base import IStorage, StorageFile

# 延迟导入 aioboto3（可选依赖）
try:
    import aioboto3
    from botocore.config import Config
    _AIOBOTO3_AVAILABLE = True
except ImportError:
    _AIOBOTO3_AVAILABLE = False
    # 创建占位符类型，避免类型检查错误
    if TYPE_CHECKING:
        import aioboto3
        from botocore.config import Config
    else:
        aioboto3 = None
        Config = None


class S3Storage(IStorage):
    """S3协议存储实现。"""
    
    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str | None = None,
        region: str | None = None,
        bucket_name: str | None = None,
    ):
        """初始化S3存储。
        
        Args:
            access_key_id: 访问密钥ID
            access_key_secret: 访问密钥
            endpoint: 端点URL（可选，用于MinIO等）
            region: 区域（可选）
            bucket_name: 默认桶名（可选）
        """
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._endpoint = endpoint
        self._region = region
        self._bucket_name = bucket_name
        self._session: aioboto3.Session | None = None
    
    async def initialize(self) -> None:
        """初始化连接。"""
        if not _AIOBOTO3_AVAILABLE:
            raise ImportError(
                "aioboto3 未安装。请安装可选依赖: pip install 'aurimyth-foundation-kit[storage-s3]'"
            )
        
        try:
            self._session = aioboto3.Session()
            logger.info("S3存储初始化成功")
        except Exception as exc:
            logger.error(f"S3连接失败: {exc}")
            raise
    
    async def _get_client(self):
        """获取S3客户端。"""
        if not self._session:
            await self.initialize()
        
        return self._session.client(
            "s3",
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._access_key_secret,
            endpoint_url=self._endpoint,
            region_name=self._region or None,
            config=Config(s3={"addressing_style": "virtual", "signature_version": "s3v4"}),
        )
    
    async def upload_file(
        self,
        file: StorageFile,
        *,
        bucket_name: str | None = None,
    ) -> str:
        """上传文件。"""
        bucket = bucket_name or file.bucket_name or self._bucket_name
        if not bucket:
            raise ValueError("桶名未指定")
        
        async with await self._get_client() as client:
            await client.put_object(
                Bucket=bucket,
                Key=file.object_name,
                Body=file.data.read() if file.data else b"",
                ContentType=file.content_type,
                Metadata=file.metadata or {},
            )
            
            if self._endpoint:
                url = f"{self._endpoint}/{bucket}/{file.object_name}"
            else:
                url = f"s3://{bucket}/{file.object_name}"
            
            logger.debug(f"S3文件上传成功: {url}")
            return url
    
    async def upload_files(
        self,
        files: list[StorageFile],
        *,
        bucket_name: str | None = None,
    ) -> list[str]:
        """批量上传文件。"""
        return await asyncio.gather(*(self.upload_file(f, bucket_name=bucket_name) for f in files))
    
    async def delete_file(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> None:
        """删除文件。"""
        bucket = bucket_name or self._bucket_name
        if not bucket:
            raise ValueError("桶名未指定")
        
        async with await self._get_client() as client:
            await client.delete_object(Bucket=bucket, Key=object_name)
            logger.debug(f"S3文件删除成功: {bucket}/{object_name}")
    
    async def get_file_url(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
        expires_in: int | None = None,
    ) -> str:
        """获取文件URL。"""
        bucket = bucket_name or self._bucket_name
        if not bucket:
            raise ValueError("桶名未指定")
        
        async with await self._get_client() as client:
            if expires_in:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": object_name},
                    ExpiresIn=expires_in,
                )
            else:
                if self._endpoint:
                    url = f"{self._endpoint}/{bucket}/{object_name}"
                else:
                    url = f"s3://{bucket}/{object_name}"
            
            return url
    
    async def file_exists(
        self,
        object_name: str,
        *,
        bucket_name: str | None = None,
    ) -> bool:
        """检查文件是否存在。"""
        bucket = bucket_name or self._bucket_name
        if not bucket:
            return False
        
        try:
            async with await self._get_client() as client:
                await client.head_object(Bucket=bucket, Key=object_name)
                return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """关闭连接。"""
        self._session = None
        logger.info("S3连接已关闭")


__all__ = [
    "S3Storage",
]


