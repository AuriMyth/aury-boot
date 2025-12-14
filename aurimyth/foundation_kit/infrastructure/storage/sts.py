"""STS 临时凭证签发（面向任意 client：Web/移动端/桌面端/Server-to-Server）。

设计目标（SDK 友好）：
- 本模块不读取环境变量、不依赖 application 层配置
- 只提供 Pydantic(BaseModel) 做入参/配置校验 + 显式调用 `issue()`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator, model_validator

from aurimyth.foundation_kit.common.logging import logger
from aurimyth.foundation_kit.infrastructure.storage.exceptions import StorageBackendError

try:
    import aioboto3

    _AIOBOTO3_AVAILABLE = True
except ImportError:
    _AIOBOTO3_AVAILABLE = False
    if TYPE_CHECKING:  # pragma: no cover
        import aioboto3
    else:  # pragma: no cover
        aioboto3 = None


class StorageSTSAction(str, Enum):
    """client 侧允许申请的动作集合（受控，避免用户传入 s3:*）。"""

    GET_OBJECT = "get_object"
    PUT_OBJECT = "put_object"


class StorageSTSRequest(BaseModel):
    """client 申请临时凭证的请求。

建议策略：
- 更安全：传 object_key（仅允许访问单个对象）
- 更灵活：传 prefix（允许访问 prefix 下的对象）
"""

    bucket_name: str | None = Field(default=None, description="桶名（可选；为空则使用服务端默认/允许的桶）")
    object_key: str | None = Field(default=None, description="精确对象 key（更安全）")
    prefix: str | None = Field(default=None, description="允许的对象前缀（更灵活）")
    actions: list[StorageSTSAction] = Field(
        default_factory=lambda: [StorageSTSAction.PUT_OBJECT],
        description="允许的操作（默认 put_object）",
        min_length=1,
    )
    duration_seconds: int | None = Field(
        default=None,
        description="凭证有效期（秒）。为空则使用服务端默认。",
        ge=60,
        le=43200,
    )

    @model_validator(mode="after")
    def _validate_scope(self) -> "StorageSTSRequest":
        if not self.object_key and not self.prefix:
            raise ValueError("必须提供 object_key 或 prefix 之一")
        if self.object_key and self.prefix:
            raise ValueError("object_key 与 prefix 只能二选一（建议使用 object_key）")
        return self

    @field_validator("object_key", "prefix")
    @classmethod
    def _validate_key_like(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip()
        if not s:
            return None
        if s.startswith("/"):
            raise ValueError("不允许以 / 开头")
        if ".." in s.split("/"):
            raise ValueError("不允许包含 .. 段")
        return s


class StorageSTSCredentials(BaseModel):
    access_key_id: str = Field(..., description="临时 AccessKeyId")
    secret_access_key: str = Field(..., description="临时 SecretAccessKey")
    session_token: str = Field(..., description="临时 SessionToken")
    expires_at: datetime = Field(..., description="过期时间（UTC）")

    # 这些字段用于 client SDK 组装请求（可选）
    region: str | None = Field(default=None, description="区域")
    endpoint: str | None = Field(default=None, description="S3 端点（MinIO/私有云场景）")
    bucket_name: str = Field(..., description="桶名")

    assumed_role_arn: str | None = Field(default=None, description="AssumeRole 返回的角色 ARN（可选）")


class StorageSTSConfig(BaseModel):
    """STS 签发配置（Pydantic 校验；由调用方显式传入）。"""

    enabled: bool = Field(default=True, description="是否启用 STS 签发能力（由调用方控制）")

    # AssumeRole 目标角色（建议使用专用、权限受控的角色）
    role_arn: str = Field(..., description="AssumeRole RoleArn（必填）")
    role_session_name: str = Field(default="aurimyth-client", description="AssumeRole RoleSessionName")
    external_id: str | None = Field(default=None, description="AssumeRole ExternalId（可选）")

    # 默认有效期（client 建议短一些）
    duration_seconds: int = Field(default=900, ge=60, le=43200, description="默认 DurationSeconds")

    # STS 端点/区域（非 AWS 或需要指定时使用）
    sts_endpoint: str | None = Field(default=None, description="STS endpoint（可选）")
    sts_region: str | None = Field(default=None, description="STS region（可选）")

    # client 最终访问的 S3 endpoint/region（供 client SDK 使用；可与 STS 不同）
    s3_endpoint: str | None = Field(default=None, description="S3 endpoint（返回给 client）")
    s3_region: str | None = Field(default=None, description="S3 region（返回给 client）")

    # 桶与前缀白名单（强烈建议配置）
    allowed_buckets: list[str] = Field(default_factory=list, description="允许签发的 bucket 白名单（为空表示不限制）")
    allowed_prefixes: list[str] = Field(default_factory=list, description="允许签发的 prefix 白名单（为空表示不限制）")

    # 可选：用于调用 STS 的源凭证（生产建议用默认链/IRSA；此处只做透传）
    source_access_key_id: str | None = Field(default=None, description="调用 STS 的源 AccessKeyId（可选）")
    source_access_key_secret: str | None = Field(default=None, description="调用 STS 的源 SecretAccessKey（可选）")
    source_session_token: str | None = Field(default=None, description="调用 STS 的源 SessionToken（可选）")

    @field_validator("allowed_prefixes")
    @classmethod
    def _normalize_prefixes(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for p in v or []:
            p2 = str(p).strip()
            if not p2:
                continue
            if p2.startswith("/"):
                p2 = p2[1:]
            out.append(p2)
        return out


def _s3_arn(bucket: str, key: str | None = None) -> str:
    if not key:
        return f"arn:aws:s3:::{bucket}"
    return f"arn:aws:s3:::{bucket}/{key}"


def _build_inline_policy(
    *,
    bucket: str,
    scope_key: str | None,
    scope_prefix: str | None,
    actions: list[StorageSTSAction],
) -> dict[str, Any]:
    object_actions: list[str] = []
    for a in actions:
        if a == StorageSTSAction.GET_OBJECT:
            object_actions.append("s3:GetObject")
        elif a == StorageSTSAction.PUT_OBJECT:
            object_actions.append("s3:PutObject")

    object_actions = sorted(set(object_actions))
    if not object_actions:
        raise ValueError("actions 不能为空")

    if scope_key:
        res = [_s3_arn(bucket, scope_key)]
    else:
        prefix = (scope_prefix or "").rstrip("/")
        res = [_s3_arn(bucket, f"{prefix}/*" if prefix else "*")]

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ClientObjectAccess",
                "Effect": "Allow",
                "Action": object_actions,
                "Resource": res,
            }
        ],
    }


class StorageSTSIssuer:
    """签发 STS 临时凭证（通用 client）。"""

    def __init__(self, config: StorageSTSConfig) -> None:
        self._config = config

    def _require_aioboto3(self) -> None:
        if not _AIOBOTO3_AVAILABLE:
            raise ImportError(
                "aioboto3 未安装。请安装可选依赖: uv add \"aurimyth-foundation-kit[storage-s3]\" 或 pip install aioboto3"
            )

    def _check_bucket_and_scope(self, req: StorageSTSRequest, bucket: str) -> None:
        st = self._config
        if st.allowed_buckets and bucket not in set(st.allowed_buckets):
            raise StorageBackendError(f"bucket 不允许: {bucket}")

        scope = req.object_key or req.prefix or ""
        if st.allowed_prefixes:
            ok = any(scope.startswith(p) for p in st.allowed_prefixes)
            if not ok:
                raise StorageBackendError("prefix/object_key 不在允许范围内")

    async def issue(self, req: StorageSTSRequest) -> StorageSTSCredentials:
        st = self._config
        if not st.enabled:
            raise StorageBackendError("STS 签发未启用（enabled=false）")

        self._require_aioboto3()

        bucket = req.bucket_name or (st.allowed_buckets[0] if st.allowed_buckets else None)
        if not bucket:
            raise StorageBackendError("未指定 bucket，且服务端未配置 allowed_buckets")

        self._check_bucket_and_scope(req, bucket)

        duration = req.duration_seconds or st.duration_seconds
        policy = _build_inline_policy(
            bucket=bucket,
            scope_key=req.object_key,
            scope_prefix=req.prefix,
            actions=req.actions,
        )

        session = aioboto3.Session()
        try:
            async with session.client(
                "sts",
                aws_access_key_id=st.source_access_key_id,
                aws_secret_access_key=st.source_access_key_secret,
                aws_session_token=st.source_session_token,
                endpoint_url=st.sts_endpoint,
                region_name=st.sts_region or None,
            ) as sts:
                params: dict[str, Any] = {
                    "RoleArn": st.role_arn,
                    "RoleSessionName": st.role_session_name,
                    "DurationSeconds": int(duration),
                    "Policy": json.dumps(policy, separators=(",", ":")),
                }
                if st.external_id:
                    params["ExternalId"] = st.external_id

                resp = await sts.assume_role(**params)
        except Exception as exc:
            logger.warning(f"STS AssumeRole 失败: {exc}")
            raise StorageBackendError("STS 签发失败") from exc

        c = resp["Credentials"]
        exp: datetime = c["Expiration"]
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        assumed_role_arn = None
        try:
            assumed_role_arn = resp.get("AssumedRoleUser", {}).get("Arn")
        except Exception:
            assumed_role_arn = None

        return StorageSTSCredentials(
            access_key_id=c["AccessKeyId"],
            secret_access_key=c["SecretAccessKey"],
            session_token=c["SessionToken"],
            expires_at=exp,
            region=st.s3_region,
            endpoint=st.s3_endpoint,
            bucket_name=bucket,
            assumed_role_arn=assumed_role_arn,
        )


__all__ = [
    "StorageSTSAction",
    "StorageSTSConfig",
    "StorageSTSCredentials",
    "StorageSTSRequest",
    "StorageSTSIssuer",
]


