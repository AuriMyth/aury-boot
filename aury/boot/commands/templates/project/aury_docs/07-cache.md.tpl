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
await session_cache.initialize(
    backend="redis",
    url="redis://localhost:6379/1",  # 使用不同的 Redis DB
)
await rate_limit_cache.initialize(
    backend="memory",
    max_size=10000,
)
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

## 7.5 API 响应缓存装饰器

使用 `@cache.cache_response()` 装饰器自动缓存 API 响应：

```python
cache = CacheManager.get_instance()

# 基本用法：自动生成缓存键
@router.get("/{{id}}")
@cache.cache_response(expire=300)
async def get_todo(id: UUID, service: TodoService = Depends(get_service)):
    entity = await service.get(id)
    return BaseResponse(code=200, message="获取成功", data=TodoResponse.model_validate(entity))

# 自定义缓存键
@router.get("/{{id}}")
@cache.cache_response(
    expire=300,
    key_builder=lambda id, **kwargs: f"todo:{{id}}"
)
async def get_todo(id: UUID, service: TodoService = Depends(get_service)):
    entity = await service.get(id)
    return BaseResponse(code=200, message="获取成功", data=TodoResponse.model_validate(entity))
```

## 7.6 模式删除（delete_pattern）

使用通配符批量删除缓存：

```python
# 删除所有 todo 相关缓存
await cache.delete_pattern("api:todo:*")

# 删除所有列表缓存
await cache.delete_pattern("api:todo:list:*")
```

## 7.7 缓存清理策略

数据变更时应及时清理相关缓存：

```python
# 更新时清理缓存
@router.put("/{{id}}")
async def update_todo(id: UUID, data: TodoUpdate, service: TodoService = Depends(get_service)):
    entity = await service.update(id, data)
    
    # 清理单个 + 模式删除
    await cache.delete(f"api:todo:{{id}}")
    await cache.delete_pattern("api:todo:list:*")  # 清理所有列表缓存
    
    return BaseResponse(code=200, message="更新成功", data=TodoResponse.model_validate(entity))

# 删除时清理缓存
@router.delete("/{{id}}")
async def delete_todo(id: UUID, service: TodoService = Depends(get_service)):
    await service.delete(id)
    await cache.delete(f"api:todo:{{id}}")
    await cache.delete_pattern("api:todo:*")  # 清理所有相关缓存
    return BaseResponse(code=200, message="删除成功", data=None)
```

### 7.7.1 缓存键命名规范

```python
# 推荐格式：{{layer}}:{{resource}}:{{identifier}}
f"api:todo:{{id}}"           # 单个资源
f"api:todo:list:{{page}}"    # 列表
f"api:todo:statistics"       # 统计
f"service:user:{{user_id}}"  # Service 层缓存
```
