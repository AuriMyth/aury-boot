# 19. 对象存储指南

对象存储模块基于 [aury-sdk-storage](https://github.com/AuriMyth/aury-sdk-storage) 实现，支持 S3 兼容存储（AWS S3、腾讯云 COS、阿里云 OSS、MinIO 等）和 STS 临时凭证签发。

## 安装

```bash
# 完整安装（S3/COS/OSS + STS 支持）
uv add "aury-sdk-storage[aws]"
# 或
pip install "aury-sdk-storage[aws]"
```

## 基本用法（StorageManager）

框架提供 `StorageManager` 单例管理器，支持命名多实例。内部由 `aury-sdk-storage` 的 `StorageFactory.from_config()` 创建具体后端（COS 原生 / S3 兼容等），对上层暴露统一接口：

```python
from io import BytesIO
from aury.boot.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

# 获取默认实例
storage = StorageManager.get_instance()

# 命名实例（如源存储和目标存储）
source = StorageManager.get_instance("source")
target = StorageManager.get_instance("target")

# 初始化（一般由 StorageComponent 自动完成，以下仅演示手动调用）
await storage.initialize(StorageConfig(
    backend=StorageBackend.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
    endpoint="https://cos.ap-guangzhou.myqcloud.com",
    access_key_id="AKIDxxxxx",
    access_key_secret="xxxxx",
))

# 上传文件（返回 URL）
url = await storage.upload_file(
    StorageFile(
        object_name="user/123/avatar.png",
        data=BytesIO(image_bytes),
        content_type="image/png",
    )
)

# 批量上传
urls = await storage.upload_files([
    StorageFile(object_name="img/1.jpg", data=b"..."),
    StorageFile(object_name="img/2.jpg", data=b"..."),
])

# 下载文件
content = await storage.download_file("user/123/avatar.png")

# 获取预签名 URL（有效期 1 小时）
url = await storage.get_file_url("user/123/avatar.png", expires_in=3600)

# 检查文件是否存在
exists = await storage.file_exists("user/123/avatar.png")

# 删除文件
await storage.delete_file("user/123/avatar.png")
```

## 本地存储（开发测试）

```python
from aury.boot.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

storage = StorageManager.get_instance()
await storage.initialize(StorageConfig(
    backend=StorageBackend.LOCAL,
    base_path="./dev_storage",
))

url = await storage.upload_file(
    StorageFile(object_name="test.txt", data=b"hello")
)
# url: file:///path/to/dev_storage/default/test.txt
```

## 高级用法：直接使用 SDK 工厂 / StorageType

在需要更精细控制后端类型（如在基础设施层扩展存储实现）时，可以直接使用 `aury.boot.infrastructure.storage` 中导出的 SDK 类型：

```python
from aury.boot.infrastructure.storage import (
    COSStorage,
    LocalStorage,
    S3Storage,
    SDKStorageFactory,  # SDK 工厂（基于 StorageType 枚举）
    StorageConfig,
    StorageFile,
    StorageType,
)

# 使用 StorageType 创建后端
config = StorageConfig(
    backend=StorageType.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
)

backend = SDKStorageFactory.from_config(config)
result = await backend.upload_file(
    StorageFile(object_name="dev/test.txt", data=b"hello"),
)
print(result.url)
```

> 一般业务代码直接通过 `StorageManager` 即可，只有在需要自定义装配流程或编写基础设施扩展时，才需要直接使用 `SDKStorageFactory` / `StorageType` / `COSStorage` 等类型。

## STS 临时凭证（前端直传）

STS（Security Token Service）用于生成临时访问凭证，适合以下场景：
- **前端直传**：后端签发临时凭证，前端使用 S3 SDK 直接上传
- **权限隔离**：每个用户只能访问自己的目录
- **最小权限**：只授予必要的操作权限

```python
from aury.sdk.storage.sts import (
    STSProviderFactory, ProviderType, STSRequest, ActionType,
)

# 创建腾讯云 STS Provider
provider = STSProviderFactory.create(
    ProviderType.TENCENT,
    secret_id="AKIDxxxxx",
    secret_key="xxxxx",
)

# 签发临时上传凭证
credentials = await provider.get_credentials(
    STSRequest(
        bucket="my-bucket-1250000000",
        region="ap-guangzhou",
        allow_path="user/123/",  # 只允许访问该目录
        action_type=ActionType.WRITE,
        duration_seconds=900,  # 15 分钟
    )
)

# 返回给前端
return {
    "accessKeyId": credentials.access_key_id,
    "secretAccessKey": credentials.secret_access_key,
    "sessionToken": credentials.session_token,
    "expiration": credentials.expiration.isoformat(),
    "bucket": credentials.bucket,
    "region": credentials.region,
    "endpoint": credentials.endpoint,
}
```

### 操作类型

```python
from aury.sdk.storage.sts import ActionType

# 只读权限（下载/查看）
ActionType.READ

# 只写权限（上传）
ActionType.WRITE

# 读写全部权限
ActionType.ALL
```

## API 集成示例

### 头像上传

```python
from io import BytesIO
from fastapi import File, UploadFile
from aury.boot.application.interfaces.egress import BaseResponse
from aury.boot.infrastructure.storage import StorageManager, StorageFile

storage = StorageManager.get_instance()

@router.post("/users/{user_id}/avatar")
async def upload_avatar(
    user_id: str,
    file: UploadFile = File(...)
):
    """用户上传头像"""
    
    # 验证文件类型
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise ValueError("只支持 JPG 和 PNG 格式")
    
    # 验证文件大小（最大 5MB）
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("文件过大")
    
    # 上传到存储
    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    url = await storage.upload_file(
        StorageFile(
            object_name=f"avatars/{user_id}.{ext}",
            data=BytesIO(content),
            content_type=file.content_type,
        )
    )
    
    return BaseResponse(code=200, message="头像上传成功", data={"url": url})
```

### 获取上传凭证 API

```python
from pydantic import BaseModel
from aury.sdk.storage.sts import (
    STSProviderFactory, ProviderType, STSRequest, ActionType, STSRequestError,
)

# 全局 Provider（复用 HTTP 连接）
sts_provider = STSProviderFactory.create(
    ProviderType.TENCENT,
    secret_id="your-secret-id",
    secret_key="your-secret-key",
)

class UploadCredentialsResponse(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: str
    bucket: str
    region: str
    endpoint: str

@router.get("/upload-credentials")
async def get_upload_credentials(user_id: str) -> BaseResponse[UploadCredentialsResponse]:
    """获取前端直传凭证"""
    try:
        credentials = await sts_provider.get_credentials(
            STSRequest(
                bucket="my-bucket-1250000000",
                region="ap-guangzhou",
                allow_path=f"user/{user_id}/",
                action_type=ActionType.WRITE,
                duration_seconds=1800,
            )
        )
        return BaseResponse(
            code=200,
            message="获取成功",
            data=UploadCredentialsResponse(
                access_key_id=credentials.access_key_id,
                secret_access_key=credentials.secret_access_key,
                session_token=credentials.session_token,
                expiration=credentials.expiration.isoformat(),
                bucket=credentials.bucket,
                region=credentials.region,
                endpoint=credentials.endpoint,
            ),
        )
    except STSRequestError as e:
        raise HTTPException(status_code=500, detail=f"STS error: {e.message}")
```

### 文件下载

```python
from fastapi.responses import StreamingResponse

@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    """下载文件"""
    
    # 获取文件信息
    file_info = await db.get_file(file_id)
    if not file_info:
        raise NotFoundError("文件不存在")
    
    # 从存储下载
    content = await storage.download_file(file_info.object_name)
    
    return StreamingResponse(
        iter([content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_info.filename}"}
    )
```

## 直接使用 SDK

如果不需要 `StorageManager`，可以直接使用 SDK：

```python
from aury.sdk.storage.storage import (
    S3Storage, StorageConfig, StorageBackend, StorageFile,
)

config = StorageConfig(
    backend=StorageBackend.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
    endpoint="https://cos.ap-guangzhou.myqcloud.com",
    access_key_id="your-access-key",
    access_key_secret="your-secret-key",
)

storage = S3Storage(config)

# 上传
result = await storage.upload_file(
    StorageFile(
        object_name="user/123/test.txt",
        data=b"Hello, World!",
        content_type="text/plain",
    )
)
print(f"Uploaded: {result.url}")
```

## 环境变量配置

```bash
# .env

# 是否启用存储组件
STORAGE_ENABLED=true

# 存储类型: local / s3 / cos / oss
STORAGE_TYPE=cos

# === 本地存储（开发环境）===
# STORAGE_TYPE=local
# STORAGE_BASE_PATH=./storage

# === S3/COS/OSS 通用配置 ===
STORAGE_ACCESS_KEY_ID=AKIDxxxxx
STORAGE_ACCESS_KEY_SECRET=xxxxx
STORAGE_ENDPOINT=https://cos.ap-guangzhou.myqcloud.com
STORAGE_REGION=ap-guangzhou
STORAGE_BUCKET_NAME=my-bucket-1250000000

# 可选：临时凭证 Session Token
# STORAGE_SESSION_TOKEN=

# 可选：STS AssumeRole（服务端自动刷新凭证）
# STORAGE_ROLE_ARN=qcs::cam::uin/100000000001:roleName/my-role
# STORAGE_ROLE_SESSION_NAME=aurimyth-storage
# STORAGE_STS_DURATION_SECONDS=3600
```

## 支持的存储后端

| 后端 | StorageBackend | 说明 |
|------|----------------|------|
| 本地存储 | `LOCAL` | 开发测试用，文件保存到本地目录 |
| AWS S3 | `S3` | Amazon S3 |
| 腾讯云 COS | `COS` | S3 兼容协议 |
| 阿里云 OSS | `OSS` | S3 兼容协议 |
| MinIO | `MINIO` | 私有化部署，S3 兼容 |

## 错误处理

```python
from aury.sdk.storage import (
    StorageSDKError,
    STSError,
    STSRequestError,
    StorageError,
    StorageBackendError,
)

try:
    credentials = await provider.get_credentials(request)
except STSRequestError as e:
    # API 调用失败（凭证错误、权限不足等）
    print(f"API 错误: [{e.code}] {e.message}")
    print(f"RequestId: {e.request_id}")  # 用于向云厂商提工单
except STSError as e:
    # 其他 STS 错误（网络错误等）
    print(f"STS 错误: {e}")

try:
    await storage.upload_file(file)
except StorageBackendError as e:
    print(f"存储后端错误: {e}")
except StorageError as e:
    print(f"存储错误: {e}")
```

---

**总结**：
- 使用 `StorageManager.get_instance()` 获取存储管理器（支持命名多实例）
- 本地开发使用 `StorageBackend.LOCAL`，生产使用 S3 兼容存储
- 前端直传场景使用 STS 临时凭证，实现权限隔离和最小权限原则
