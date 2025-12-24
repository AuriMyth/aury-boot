# 缓存

框架的 `CacheManager` 支持**命名多实例**，可以为不同用途配置不同的缓存后端。

## 7.1 基本用法

```python
from aury.boot.infrastructure.cache import CacheManager

# 默认实例
cache = CacheManager.get_instance()
await cache.set("key", value, expire=300)  # 5 分钟
value = await cache.get("key")
await cache.delete("key")
```

## 7.2 多实例使用

```python
# 获取不同用途的缓存实例
session_cache = CacheManager.get_instance("session")
rate_limit_cache = CacheManager.get_instance("rate_limit")

# 分别初始化（可以使用不同的后端或配置）
await session_cache.init_app({{
    "CACHE_TYPE": "redis",
    "CACHE_URL": "redis://localhost:6379/1",  # 使用不同的 Redis DB
}})
await rate_limit_cache.init_app({{
    "CACHE_TYPE": "memory",
    "CACHE_MAX_SIZE": 10000,
}})
```

## 7.3 缓存装饰器

```python
cache = CacheManager.get_instance()

@cache.cached(expire=300, key_prefix="user")
async def get_user(user_id: int):
    # 缓存键自动生成：user:<func_name>:<args_hash>
    return await repo.get(user_id)
```

## 7.4 支持的后端

- `redis` - Redis（推荐生产用）
- `memory` - 内存缓存（开发/测试用）
- `memcached` - Memcached
