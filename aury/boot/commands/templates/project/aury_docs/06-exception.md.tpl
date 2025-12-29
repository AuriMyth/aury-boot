# 异常处理

框架提供了统一的异常处理机制，所有异常都会被全局异常处理中间件捕获并转换为标准的 HTTP 响应。

## 6.1 异常处理流程

```
请求 → API 路由 → Service → Repository → 抛出异常
                                              ↓
                              全局异常处理中间件（Middleware）
                                              ↓
                                  转换为 ErrorResponse Schema
                                              ↓
                                       JSON 响应返回客户端
```

**流程说明**：
1. 业务代码抛出异常（如 `NotFoundError`）
2. 框架的全局异常处理中间件自动捕获
3. 根据异常类型转换为对应的 HTTP 状态码和错误响应
4. 返回统一格式的 JSON 错误响应

**响应格式**：
```json
{{
  "code": "NOT_FOUND",
  "message": "用户不存在",
  "data": null
}}
```

## 6.2 内置异常

```python
from aury.boot.application.errors import (
    BaseError,
    NotFoundError,       # 404
    AlreadyExistsError,  # 409
    ValidationError,     # 422
    UnauthorizedError,   # 401
    ForbiddenError,      # 403
    BusinessError,       # 400
)

# 使用示例
raise NotFoundError("用户不存在", resource=user_id)
raise AlreadyExistsError(f"邮箱 {{email}} 已被注册")
raise UnauthorizedError("未登录或登录已过期")
```

## 6.3 自定义异常

**文件**: `{package_name}/exceptions/order.py`

```python
from enum import Enum
from fastapi import status
from aury.boot.application.errors import BaseError


# 推荐：定义错误码枚举
class OrderErrorCode(str, Enum):
    ORDER_ERROR = "5000"
    ORDER_NOT_FOUND = "5001"
    INSUFFICIENT_STOCK = "5002"
    PAYMENT_FAILED = "5003"


class OrderError(BaseError):
    default_message = "订单错误"
    default_code = OrderErrorCode.ORDER_ERROR
    default_status_code = status.HTTP_400_BAD_REQUEST


class OrderNotFoundError(OrderError):
    default_message = "订单不存在"
    default_code = OrderErrorCode.ORDER_NOT_FOUND
    default_status_code = status.HTTP_404_NOT_FOUND


class InsufficientStockError(OrderError):
    default_message = "库存不足"
    default_code = OrderErrorCode.INSUFFICIENT_STOCK
    default_status_code = status.HTTP_400_BAD_REQUEST


# 使用
raise OrderNotFoundError()  # 使用默认值
raise OrderError(message="订单ID无效")  # 自定义消息
raise InsufficientStockError(message=f"商品 {{product_id}} 库存不足")
```

**Error Code 规范**：
- **推荐使用枚举**定义错误码，枚举值必须为数字字符串（如 `"5001"`）
- 框架预留编码范围：1xxx 通用、2xxx 数据库、3xxx 业务、4xxx 外部服务、**5xxx+ 用户自定义**

## 6.4 异常与 Schema 的关系

异常处理中间件会自动将异常转换为 Schema 响应：

```python
# Service 层抛出异常
raise NotFoundError("用户不存在")

# 中间件捕获并转换为响应
# HTTP 状态码：404
# 响应体：
# {{
#   "code": "NOT_FOUND",
#   "message": "用户不存在",
#   "data": null
# }}
```

**最佳实践**：
- 在 Service 层抛出业务异常，不要在 API 层手动处理
- 使用框架内置异常或自定义异常，不要直接抛出 `Exception`
- 自定义异常继承 `BaseError`，框架会自动处理
