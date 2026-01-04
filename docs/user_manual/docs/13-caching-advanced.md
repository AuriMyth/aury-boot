# 12. 缓存系统高级用法

请参考 [00-quick-start.md](./00-quick-start.md) 第 12 章的基础用法。

## 高级特性

### 获取缓存实例

```python
from aury.boot.infrastructure.cache import CacheManager

# 默认实例
cache = CacheManager.get_instance()

# 命名多实例（如会话缓存、限流缓存）
# session_cache = CacheManager.get_instance("session")
# rate_limit_cache = CacheManager.get_instance("rate_limit")
```

### 装饰器缓存

```python
cache = CacheManager.get_instance()

# 自动缓存函数结果
@cache.cached(expire=60, key_prefix="user_profile")
async def get_user_profile(user_id: str):
    # 第一次调用时执行，结果缓存 60 秒
    # 后续调用直接返回缓存结果
    return await db.get_user(user_id)
```

### 缓存失效

```python
# 手动清除单个缓存
await cache.delete("user:123")

# 清除多个缓存
await cache.delete("user:123", "user:456")

# 清除所有缓存
await cache.clear()
```

### 缓存配置

在 `.env` 中配置：

```bash
# 内存缓存（开发环境）
CACHE__CACHE_TYPE=memory
CACHE__MAX_SIZE=1000

# Redis（生产环境）
CACHE__CACHE_TYPE=redis
CACHE__URL=redis://localhost:6379/0
```

### 多实例配置

支持多实例，环境变量格式：`CACHE__{INSTANCE}__{FIELD}`

```bash
# 默认实例
CACHE__CACHE_TYPE=redis
CACHE__URL=redis://localhost:6379/0

# 会话缓存实例
CACHE__SESSION__CACHE_TYPE=redis
CACHE__SESSION__URL=redis://localhost:6379/2
CACHE__SESSION__DEFAULT_TTL=3600

# 限流缓存实例
CACHE__RATE_LIMIT__CACHE_TYPE=memory
CACHE__RATE_LIMIT__MAX_SIZE=10000
```

代码中使用：

```python
# 默认实例
cache = CacheManager.get_instance()

# 命名实例
session_cache = CacheManager.get_instance("session")
rate_limit_cache = CacheManager.get_instance("rate_limit")
```

## 缓存策略

### Cache-Aside（推荐）

```python
async def get_user(user_id: str):
    cache_key = f"user:{user_id}"
    
    # 1. 尝试从缓存获取
    user = await cache.get(cache_key)
    if user:
        return user
    
    # 2. 缓存未命中，从数据库获取
    user = await db.get_user(user_id)
    if user:
        # 3. 写入缓存
        await cache.set(cache_key, user, expire=300)
    
    return user
```

### Write-Through（强一致性）

```python
async def update_user(user_id: str, data: dict):
    # 1. 更新数据库
    user = await db.update_user(user_id, data)
    
    # 2. 更新缓存
    cache_key = f"user:{user_id}"
    await cache.set(cache_key, user, expire=300)
    
    return user
```

### Write-Behind（高性能）

```python
async def update_user_async(user_id: str, data: dict):
    # 1. 更新缓存
    cache_key = f"user:{user_id}"
    await cache.set(cache_key, data, expire=300)
    
    # 2. 异步更新数据库
    await task_queue.send(update_user_in_db_task, user_id=user_id, data=data)
    
    return data
```

## 常见模式

### 列表缓存

```python
async def get_user_list(page: int = 1, size: int = 20):
    cache_key = f"users:page:{page}:size:{size}"
    
    # 尝试从缓存获取
    result = await cache.get(cache_key)
    if result:
        return result
    
    # 从数据库获取
    users, total = await db.list_users(page=page, size=size)
    result = {"users": users, "total": total}
    
    # 缓存 1 小时
    await cache.set(cache_key, result, expire=3600)
    return result
```

### 计数缓存

```python
async def get_user_count():
    cache_key = "users:count"
    
    count = await cache.get(cache_key)
    if count is not None:
        return count
    
    count = await db.count_users()
    await cache.set(cache_key, count, expire=300)
    return count

async def update_user_count():
    """更新用户计数缓存。"""
    cache_key = "users:count"
    
    # 重新计算并更新缓存
    count = await db.count_users()
    await cache.set(cache_key, count, expire=300)
    return count
```

### 热数据预热

```python
async def warm_cache():
    """应用启动时预热缓存"""
    
    # 加载常用数据
    configs = await db.get_all_configs()
    for config in configs:
        cache_key = f"config:{config.key}"
        await cache.set(cache_key, config, expire=3600)
    
    logger.info(f"已预热 {len(configs)} 个配置到缓存")

# 在组件中调用
class CacheWarmupComponent(Component):
    name = "cache_warmup"
    enabled = True
    depends_on = ["cache"]
    
    async def setup(self, app: FoundationApp, config):
        await warm_cache()
```

## 性能优化

### 缓存穿透（Cache Penetration）

问题：查询不存在的数据，频繁绕过缓存

解决方案：

```python
async def get_user_safe(user_id: str):
    cache_key = f"user:{user_id}"
    
    # 使用特殊值标记不存在的数据
    user = await cache.get(cache_key)
    if user == "NOT_FOUND":
        return None
    if user:
        return user
    
    user = await db.get_user(user_id)
    if user:
        await cache.set(cache_key, user, expire=300)
    else:
        # 缓存不存在的标记（过期时间短）
        await cache.set(cache_key, "NOT_FOUND", expire=60)
    
    return user
```

### 缓存雪崩（Cache Avalanche）

问题：大量缓存同时过期

解决方案：

```python
async def get_user(user_id: str):
    cache_key = f"user:{user_id}"
    
    user = await cache.get(cache_key)
    if user:
        return user
    
    user = await db.get_user(user_id)
    if user:
        # 随机过期时间，避免同时过期
        import random
        expire = 300 + random.randint(0, 60)
        await cache.set(cache_key, user, expire=expire)
    
    return user
```

### 缓存击穿（Cache Breakdown）

问题：热点数据失效时，并发请求击穿缓存

解决方案：

```python
import asyncio

lock = asyncio.Lock()

async def get_hot_data(data_id: str):
    cache_key = f"hot:{data_id}"
    
    data = await cache.get(cache_key)
    if data:
        return data
    
    # 使用分布式锁，只有一个进程刷新缓存
    async with lock:
        # 再次检查缓存（双重检查）
        data = await cache.get(cache_key)
        if data:
            return data
        
        # 从数据库获取
        data = await db.get_hot_data(data_id)
        await cache.set(cache_key, data, expire=300)
    
    return data
```

## 监控和调试

### 缓存日志

```python
from aury.boot.common.logging import logger

async def get_user_with_logging(user_id: str):
    cache_key = f"user:{user_id}"
    
    user = await cache.get(cache_key)
    if user:
        logger.debug(f"缓存命中: {cache_key}")
        return user
    
    logger.debug(f"缓存未命中: {cache_key}")
    user = await db.get_user(user_id)
    if user:
        await cache.set(cache_key, user, expire=300)
    
    return user
```

---

**总结**：充分利用缓存可以显著提升应用性能。选择合适的缓存策略和过期时间，注意缓存穿透、雪崩、击穿等问题，才能构建稳定高效的系统。
