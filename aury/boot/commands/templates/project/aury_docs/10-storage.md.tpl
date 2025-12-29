# 对象存储（基于 aury-sdk-storage）

## 10.1 安装

```bash
# 完整安装（S3/COS/OSS + STS 支持）
uv add "aury-sdk-storage[aws]"
# 或
pip install "aury-sdk-storage[aws]"
```

## 10.2 基本用法（StorageManager）

`StorageManager` 支持**命名多实例**，可以同时管理多个存储后端。

```python
from aury.boot.infrastructure.storage import (
    StorageManager, StorageConfig, StorageBackend, StorageFile,
)

# 默认实例
storage = StorageManager.get_instance()
await storage.initialize(StorageConfig(
    backend=StorageBackend.COS,
    bucket_name="my-bucket-1250000000",
    region="ap-guangzhou",
    endpoint="https://cos.ap-guangzhou.myqcloud.com",
    access_key_id="AKIDxxxxx",
    access_key_secret="xxxxx",
))

# 多实例示例：源存储和目标存储
source = StorageManager.get_instance("source")
target = StorageManager.get_instance("target")
await source.initialize(StorageConfig(backend=StorageBackend.COS, ...))
await target.initialize(StorageConfig(backend=StorageBackend.S3, ...))

# 上传文件（返回 URL）
# data 支持: bytes / BytesIO / BinaryIO
url = await storage.upload_file(
    StorageFile(
        object_name="user/123/avatar.png",
        data=image_bytes,
        content_type="image/png",
    )
)

# 下载文件
content = await storage.download_file("user/123/avatar.png")

# 获取预签名 URL
url = await storage.get_file_url("user/123/avatar.png", expires_in=3600)

# 检查文件是否存在
exists = await storage.file_exists("user/123/avatar.png")

# 删除文件
await storage.delete_file("user/123/avatar.png")
```

## 10.3 STS 临时凭证（前端直传）

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
        allow_path="user/123/",
        action_type=ActionType.WRITE,
        duration_seconds=900,
    )
)

# 返回给前端
return {{
    "accessKeyId": credentials.access_key_id,
    "secretAccessKey": credentials.secret_access_key,
    "sessionToken": credentials.session_token,
    "expiration": credentials.expiration.isoformat(),
    "bucket": credentials.bucket,
    "region": credentials.region,
    "endpoint": credentials.endpoint,
}}
```

## 10.4 本地存储（开发测试）

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
