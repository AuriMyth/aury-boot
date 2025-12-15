"""自定义异常模块。

在此文件中定义业务异常类，继承自 BaseError。
框架的全局异常处理器会自动将这些异常转换为 HTTP 响应。

============================================================
框架已有的异常类（可直接使用）
============================================================
- BaseError: 异常基类
- ValidationError: 验证失败 (400)
- NotFoundError: 资源不存在 (404)
- AlreadyExistsError: 资源已存在 (409)
- UnauthorizedError: 未授权 (401)
- ForbiddenError: 禁止访问 (403)
- DatabaseError: 数据库错误 (500)
- BusinessError: 业务错误 (400)
- VersionConflictError: 乐观锁冲突 (409)

============================================================
框架预留错误码范围（ErrorCode 枚举）
============================================================
- 1xxx: 通用错误
    1000: UNKNOWN_ERROR
    1001: VALIDATION_ERROR
    1002: NOT_FOUND
    1003: ALREADY_EXISTS
    1004: UNAUTHORIZED
    1005: FORBIDDEN
- 2xxx: 数据库错误
    2000: DATABASE_ERROR
    2001: DUPLICATE_KEY
    2002: CONSTRAINT_VIOLATION
    2003: VERSION_CONFLICT
- 3xxx: 业务错误
    3000: BUSINESS_ERROR
    3001: INVALID_OPERATION
    3002: INSUFFICIENT_PERMISSION
- 4xxx: 外部服务错误
    4000: EXTERNAL_SERVICE_ERROR
    4001: TIMEOUT_ERROR
    4002: NETWORK_ERROR

============================================================
自定义错误码建议从 5000 开始，使用字符串格式
============================================================

继承示例：
    class OrderError(BaseError):
        default_message = "订单错误"
        default_code = "5001"  # 字符串格式
        default_status_code = 400

    class OrderNotPaidError(OrderError):
        default_message = "订单未支付"
        default_code = "5002"
"""

from fastapi import status

from aury.boot.application.errors import BaseError

# ============================================================
# 在此定义业务异常类
# ============================================================


# class OrderError(BaseError):
#     """订单相关异常基类。"""
#     default_message = "订单错误"
#     default_code = "ORDER_ERROR"
#     default_status_code = status.HTTP_400_BAD_REQUEST
#
#
# class OrderNotFoundError(OrderError):
#     """订单不存在。"""
#     default_message = "订单不存在"
#     default_code = "ORDER_NOT_FOUND"
#     default_status_code = status.HTTP_404_NOT_FOUND
#
#
# class OrderNotPaidError(OrderError):
#     """订单未支付。"""
#     default_message = "订单未支付"
#     default_code = "ORDER_NOT_PAID"
