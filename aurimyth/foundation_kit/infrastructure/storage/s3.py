"""S3 存储实现。

支持 AWS S3、MinIO 等兼容 S3 协议的对象存储服务。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.storage.base import IStorage, StorageFile
from aurimyth.foundation_kit.infrastructure.storage.exceptions import StorageBackendError
from pydantic import BaseModel

try:
    # Pydantic v2
    from pydantic import ConfigDict
except Exception:  # pragma: no cover
    ConfigDict = None  # type: ignore[assignment]

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


class S3Credentials(BaseModel):
    """S3/STS 使用的凭证三件套（可带过期时间）。"""

    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None
    expires_at: datetime | None = None

    # 尽量保持不可变，避免在并发场景被意外修改
    if ConfigDict is not None:  # Pydantic v2
        model_config = ConfigDict(frozen=True)
    else:  # Pydantic v1
        class Config:
            frozen = True


class IS3CredentialsProvider:
    """S3 凭证提供器（支持自动刷新）。"""

    async def get_credentials(self) -> S3Credentials:
        raise NotImplementedError


class StaticCredentialsProvider(IS3CredentialsProvider):
    """静态凭证提供器（长效 AK/SK 或已拿到的临时三件套）。"""

    def __init__(
        self,
        *,
        access_key_id: str | None,
        secret_access_key: str | None,
        session_token: str | None = None,
    ) -> None:
        self._creds = S3Credentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            expires_at=None,
        )

    async def get_credentials(self) -> S3Credentials:
        return self._creds


class STSAssumeRoleProvider(IS3CredentialsProvider):
    """通过 STS AssumeRole 获取临时凭证。

    设计约束（按你的要求）：
    - **不在内部自动刷新**（避免隐式网络调用与生命周期不透明）
    - 当凭证过期时，`get_credentials()` 会抛错，要求外部显式触发刷新
    """

    def __init__(
        self,
        *,
        session: "aioboto3.Session",
        role_arn: str,
        role_session_name: str,
        external_id: str | None = None,
        duration_seconds: int = 3600,
        sts_endpoint: str | None = None,
        sts_region: str | None = None,
        source_provider: IS3CredentialsProvider | None = None,
        refresh_skew_seconds: int = 90,
    ) -> None:
        self._session = session
        self._role_arn = role_arn
        self._role_session_name = role_session_name
        self._external_id = external_id
        self._duration_seconds = duration_seconds
        self._sts_endpoint = sts_endpoint
        self._sts_region = sts_region
        self._source_provider = source_provider
        self._refresh_skew = timedelta(seconds=max(0, refresh_skew_seconds))

        self._lock = asyncio.Lock()
        self._cached: S3Credentials | None = None

    def _needs_refresh(self, creds: S3Credentials | None) -> bool:
        if creds is None:
            return True
        if creds.expires_at is None:
            return False
        now = datetime.now(timezone.utc)
        # 提前一点刷新，避免边界时刻签名失败
        return now + self._refresh_skew >= creds.expires_at

    async def _assume_role(self) -> S3Credentials:
        src = await self._source_provider.get_credentials() if self._source_provider else S3Credentials()

        # NOTE: 如果 src 为空（None），aioboto3 会走默认凭证链（env/metadata/IRSA等）
        async with self._session.client(
            "sts",
            aws_access_key_id=src.access_key_id,
            aws_secret_access_key=src.secret_access_key,
            aws_session_token=src.session_token,
            endpoint_url=self._sts_endpoint,
            region_name=self._sts_region or None,
        ) as sts:
            params: dict[str, object] = {
                "RoleArn": self._role_arn,
                "RoleSessionName": self._role_session_name,
                "DurationSeconds": self._duration_seconds,
            }
            if self._external_id:
                params["ExternalId"] = self._external_id

            resp = await sts.assume_role(**params)
            c = resp["Credentials"]
            exp: datetime | None = c.get("Expiration")
            if exp is not None and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)

            return S3Credentials(
                access_key_id=c.get("AccessKeyId"),
                secret_access_key=c.get("SecretAccessKey"),
                session_token=c.get("SessionToken"),
                expires_at=exp,
            )

    async def refresh(self) -> S3Credentials:
        """外部显式刷新（重新 AssumeRole 并更新缓存）。"""
        async with self._lock:
            self._cached = await self._assume_role()
            return self._cached

    async def get_credentials(self) -> S3Credentials:
        # 1) 首次使用：允许内部获取一次（等同于初始化拿票）
        if self._cached is None:
            return await self.refresh()

        # 2) 过期/将过期：不自动刷新，交给外部显式 refresh()
        if self._needs_refresh(self._cached):
            raise StorageBackendError("STS 临时凭证已过期/将过期，请由外部显式刷新")

        return self._cached


class S3Storage(IStorage):
    """S3协议存储实现。"""
    
    def __init__(
        self,
        access_key_id: str | None = None,
        access_key_secret: str | None = None,
        session_token: str | None = None,
        endpoint: str | None = None,
        region: str | None = None,
        bucket_name: str | None = None,
        addressing_style: str = "virtual",
        role_arn: str | None = None,
        role_session_name: str = "aurimyth-storage",
        external_id: str | None = None,
        sts_endpoint: str | None = None,
        sts_region: str | None = None,
        sts_duration_seconds: int = 3600,
    ):
        """初始化S3存储。
        
        Args:
            access_key_id: 访问密钥ID
            access_key_secret: 访问密钥
            session_token: 会话令牌（STS临时凭证）
            endpoint: 端点URL（可选，用于MinIO等）
            region: 区域（可选）
            bucket_name: 默认桶名（可选）
            addressing_style: 寻址风格（virtual/path）。MinIO 常用 path。
            role_arn: 需要 AssumeRole 的角色 ARN（启用 STS）
            role_session_name: STS 会话名
            external_id: 外部 ID（可选）
            sts_endpoint: STS 端点（可选，私有云/非AWS场景）
            sts_region: STS 区域（可选）
            sts_duration_seconds: AssumeRole DurationSeconds（默认1小时）
        """
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._session_token = session_token
        self._endpoint = endpoint
        self._region = region
        self._bucket_name = bucket_name
        self._session: aioboto3.Session | None = None

        self._addressing_style = addressing_style
        self._role_arn = role_arn
        self._role_session_name = role_session_name
        self._external_id = external_id
        self._sts_endpoint = sts_endpoint
        self._sts_region = sts_region
        self._sts_duration_seconds = sts_duration_seconds
        self._credentials_provider: IS3CredentialsProvider | None = None
        self._sts_provider: STSAssumeRoleProvider | None = None
    
    async def initialize(self) -> None:
        """初始化连接。"""
        if not _AIOBOTO3_AVAILABLE:
            raise ImportError(
                "aioboto3 未安装。请安装可选依赖: pip install 'aurimyth-foundation-kit[storage-s3]'"
            )
        
        try:
            self._session = aioboto3.Session()
            # 统一凭证来源：静态三件套 / 默认链 / STS AssumeRole
            base_provider = StaticCredentialsProvider(
                access_key_id=self._access_key_id,
                secret_access_key=self._access_key_secret,
                session_token=self._session_token,
            )
            if self._role_arn:
                self._sts_provider = STSAssumeRoleProvider(
                    session=self._session,
                    role_arn=self._role_arn,
                    role_session_name=self._role_session_name,
                    external_id=self._external_id,
                    duration_seconds=self._sts_duration_seconds,
                    sts_endpoint=self._sts_endpoint,
                    sts_region=self._sts_region,
                    source_provider=base_provider,
                )
                self._credentials_provider = self._sts_provider
            else:
                # 没有 role_arn 时：直接用静态三件套；若为空则走默认凭证链
                self._credentials_provider = base_provider
            logger.info("S3存储初始化成功")
        except Exception as exc:
            logger.error(f"S3连接失败: {exc}")
            raise
    
    async def _get_client(self):
        """获取S3客户端。"""
        if not self._session:
            await self.initialize()

        creds = await self._credentials_provider.get_credentials() if self._credentials_provider else S3Credentials()

        # 允许用户不提供 AK/SK：此时 boto 会走默认凭证链
        aws_access_key_id = creds.access_key_id or None
        aws_secret_access_key = creds.secret_access_key or None
        aws_session_token = creds.session_token or None

        style = self._addressing_style
        if style not in ("virtual", "path"):
            style = "virtual"

        return self._session.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            endpoint_url=self._endpoint,
            region_name=self._region or None,
            config=Config(s3={"addressing_style": style, "signature_version": "s3v4"}),
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
            raise StorageBackendError("桶名未指定")
        
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
            raise StorageBackendError("桶名未指定")
        
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
            raise StorageBackendError("桶名未指定")
        
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
        self._credentials_provider = None
        self._sts_provider = None
        logger.info("S3连接已关闭")

    async def refresh_credentials(self) -> None:
        """外部显式刷新 STS 临时凭证。

        仅当初始化时配置了 role_arn（启用 AssumeRole）才有效。
        """
        if not self._sts_provider:
            # 没启用 STS AssumeRole 或尚未 initialize
            return
        await self._sts_provider.refresh()


__all__ = [
    "S3Storage",
]


