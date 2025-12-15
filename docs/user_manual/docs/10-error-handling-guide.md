# 9. 错误处理完全指南

## 开发规范：异常继承原则

**核心原则**：所有服务的业务异常都必须继承 Foundation Kit 的异常类，不允许创建独立的异常体系。

这确保：
- ✅ 异常能被 Foundation Kit 的全局异常处理器正确捕获
- ✅ 自动映射到正确的 HTTP 状态码
- ✅ 统一的异常响应格式
- ✅ 便于服务间异常处理

## 异常体系

Kit 提供了标准化的异常体系，覆盖常见的应用场景。

### 标准异常

```python
from aury.boot.application.errors import (
    NotFoundError,              # 404 资源不存在
    AlreadyExistsError,         # 409 资源已存在
    UnauthorizedError,          # 401 未授权
    ForbiddenError,             # 403 无权限
    ValidationError,            # 400 验证失败
    ConflictError,              # 409 冲突
    InternalServerError,        # 500 服务器错误
    ServiceUnavailableError,    # 503 服务不可用
)

# 使用示例
@router.get("/users/{user_id}")
async def get_user(user_id: str, repo=Depends(get_user_repo)):
    user = await repo.get(user_id)
    if not user:
        raise NotFoundError(f"用户 {user_id} 不存在")
    return BaseResponse(code=200, message="获取成功", data=user)

@router.post("/users")
async def create_user(request: UserCreateRequest, repo=Depends(get_user_repo)):
    existing = await repo.get_by_email(request.email)
    if existing:
        raise AlreadyExistsError(f"邮箱 {request.email} 已被使用")
    
    user = await repo.create({"email": request.email})
    return BaseResponse(code=200, message="创建成功", data=user)
```

### 异常到 HTTP 状态码的映射

```
NotFoundError           → 404
AlreadyExistsError      → 409
UnauthorizedError       → 401
ForbiddenError          → 403
ValidationError         → 400
ConflictError           → 409
InternalServerError     → 500
ServiceUnavailableError → 503
```

## 自定义异常（遵循继承规则）

### 定义业务异常的正确方式

```python
# ✅ 正确：业务异常继承 Foundation Kit 的异常类
from aury.boot.application.errors import (
    BusinessError,
    NotFoundError,
    AlreadyExistsError,
)

class InsufficientBalanceError(BusinessError):
    """余额不足错误 - 继承 BusinessError (400)"""
    
    def __init__(self, balance: float, required: float, **kwargs):
        super().__init__(
            message=f"余额不足：需要 {required}，现有 {balance}",
            metadata={
                "balance": balance,
                "required": required,
            },
            **kwargs
        )

class OrderNotFoundError(NotFoundError):
    """订单不存在错误 - 继承 NotFoundError (404)"""
    
    def __init__(self, order_id: str, **kwargs):
        super().__init__(
            message=f"订单 {order_id} 不存在",
            resource="Order",
            metadata={"order_id": order_id},
            **kwargs
        )

class DuplicateOrderError(AlreadyExistsError):
    """订单重复错误 - 继承 AlreadyExistsError (409)"""
    
    def __init__(self, order_id: str, **kwargs):
        super().__init__(
            message=f"订单 {order_id} 已存在",
            resource="Order",
            metadata={"order_id": order_id},
            **kwargs
        )

# ❌ 错误：不要创建独立的异常体系
# from some_custom_lib import CustomAppError  # 不允许
# class OrderProcessingError(CustomAppError):  # 不允许
#     pass

# 使用
@router.post("/orders/{order_id}/pay")
async def pay_order(order_id: str, service=Depends(get_order_service)):
    try:
        result = await service.process_payment(order_id)
        return BaseResponse(code=200, message="支付成功", data=result)
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except OrderProcessingError as e:
        raise HTTPException(status_code=400, detail=e.message)
```

## 异常处理

### 全局异常处理器

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from aury.boot.application.interfaces.egress import (
    ErrorResponse,
    ResponseBuilder
)
from aury.boot.common.logging import logger

app = FastAPI()

# 处理应用异常
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未捕获的异常: {exc}", exc_info=exc)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse.create(
            code=500,
            message="服务器内部错误",
            error_code="INTERNAL_SERVER_ERROR"
        ).model_dump()
    )

# 处理验证错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(x) for x in error["loc"][1:])
        errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=400,
        content=ErrorResponse.create(
            code=400,
            message="请求参数验证失败",
            error_code="VALIDATION_ERROR",
            details={"errors": errors}
        ).model_dump()
    )

# 处理特定异常
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse.create(
            code=404,
            message=str(exc),
            error_code="NOT_FOUND"
        ).model_dump()
    )

@app.exception_handler(AlreadyExistsError)
async def already_exists_handler(request: Request, exc: AlreadyExistsError):
    return JSONResponse(
        status_code=409,
        content=ErrorResponse.create(
            code=409,
            message=str(exc),
            error_code="ALREADY_EXISTS"
        ).model_dump()
    )

@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError):
    return JSONResponse(
        status_code=401,
        content=ErrorResponse.create(
            code=401,
            message=str(exc),
            error_code="UNAUTHORIZED"
        ).model_dump()
    )
```

## 错误代码管理

### 集中管理错误代码

```python
# errors/codes.py
class ErrorCode:
    """错误代码常量"""
    
    # 用户相关
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # 订单相关
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    INVALID_ORDER_STATUS = "INVALID_ORDER_STATUS"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    
    # 验证相关
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_EMAIL = "INVALID_EMAIL"
    WEAK_PASSWORD = "WEAK_PASSWORD"

# 使用
@router.post("/users")
async def create_user(request: UserCreateRequest, service=Depends(...)):
    try:
        user = await service.create(request)
        return BaseResponse(code=200, message="创建成功", data=user)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=400,
                message=str(e),
                error_code=ErrorCode.VALIDATION_ERROR
            ).model_dump()
        )
```

## 错误日志

### 结构化错误日志

```python
from aury.boot.common.logging import logger

@router.post("/orders")
async def create_order(request: OrderRequest, service=Depends(...)):
    try:
        order = await service.create(request)
        logger.info("订单创建成功", extra={
            "order_id": order.id,
            "user_id": order.user_id,
            "amount": order.total_amount
        })
        return BaseResponse(code=200, message="创建成功", data=order)
    
    except ValidationError as e:
        logger.warning("订单验证失败", extra={
            "errors": str(e),
            "request": request.dict()
        })
        raise
    
    except Exception as e:
        logger.error("订单创建异常", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "request": request.dict()
        })
        raise
```

## 优雅的错误处理模式

### Try-Except-Else 模式

```python
@router.post("/users")
async def create_user(request: UserCreateRequest, service=Depends(...)):
    try:
        user = await service.create(request)
    except AlreadyExistsError:
        logger.warning(f"用户邮箱已存在: {request.email}")
        raise HTTPException(status_code=409, detail="邮箱已存在")
    except ValidationError as e:
        logger.warning(f"验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户异常: {e}")
        raise HTTPException(status_code=500, detail="服务器错误")
    else:
        # 成功分支
        logger.info(f"用户创建成功: {user.id}")
        return BaseResponse(code=200, message="创建成功", data=user)
```

### Context Manager 模式（事务相关）

```python
from aury.boot.domain.transaction import transactional_context

@router.post("/orders")
async def create_order(request: OrderRequest, session=Depends(...)):
    try:
        async with transactional_context(session) as txn_session:
            order_repo = OrderRepository(txn_session)
            order = await order_repo.create(request.dict())
            
            # 如果以下任何操作失败，整个事务回滚
            item_repo = OrderItemRepository(txn_session)
            for item in request.items:
                await item_repo.create({
                    "order_id": order.id,
                    **item.dict()
                })
    
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        raise HTTPException(status_code=500, detail="创建订单失败")
    
    return BaseResponse(code=200, message="创建成功", data=order)
```

## 常见问题和最佳实践

### ❌ 常见错误

```python
# 错误 1: 捕获所有异常但什么都不做
try:
    result = await operation()
except:
    pass  # ❌ 隐藏了真实错误

# 错误 2: 异常消息暴露内部细节
raise Exception(f"数据库连接失败: {db_error}")  # ❌ 暴露内部信息

# 错误 3: 没有记录异常堆栈
except Exception:
    logger.error("操作失败")  # ❌ 没有堆栈信息

# 错误 4: 重复包装异常
try:
    operation()
except Exception as e:
    raise Exception(f"操作失败: {e}")  # ❌ 丢失原始信息
```

### ✅ 最佳实践

```python
# 好 1: 捕获特定异常并适当处理
try:
    result = await operation()
except SpecificError as e:
    logger.warning(f"预期的错误: {e}")
    # 处理已知的错误
    raise HTTPException(status_code=400, detail="操作失败")
except Exception as e:
    logger.error(f"未预期的错误", exc_info=e)
    # 处理未知的错误
    raise HTTPException(status_code=500, detail="服务器错误")

# 好 2: 异常消息不暴露内部细节
try:
    connection = await connect_db()
except Exception as e:
    logger.error(f"数据库连接失败: {e}")
    # 对用户隐藏细节
    raise ServiceUnavailableError("数据库暂时不可用")

# 好 3: 记录完整的异常信息
except Exception as e:
    logger.error("操作失败", exc_info=e)  # 包含堆栈

# 好 4: 提供有用的错误上下文
except DatabaseError as e:
    logger.error("数据库操作失败", extra={
        "operation": "create_user",
        "user_email": request.email,
        "error": str(e)
    })
    raise
```

## 错误响应示例

```json
{
  "code": 400,
  "message": "请求参数验证失败",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "errors": [
      {
        "field": "email",
        "message": "invalid email format",
        "type": "value_error.email"
      },
      {
        "field": "password",
        "message": "ensure this value has at least 8 characters",
        "type": "value_error.string.too_short"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 服务异常定义的开发规范

### 异常命名约定

**规范**：`<业务对象><操作><异常类型>Error`

```
✅ 正确的命名
- UserNotFoundError       (用户不存在)
- UserInactiveError       (用户未激活)
- DuplicateUserError      (用户重复)
- InvalidCredentialsError (无效凭证)
- TokenExpiredError       (令牌过期)

❌ 不规范的命名
- UserError              (太宽泛)
- NotFoundErr            (缩写不一致)
- UserExistsAlready      (格式不一致)
```

### 异常代码范围约定

每个服务的错误代码枚举必须**继承** Foundation Kit 的 `ErrorCode`，在服务特定的范围内定义，不允许覆盖已有的错误代码：

**Foundation Kit 保留范围**（不覆盖）：
```
通用错误     (1xxx):  VALIDATION_ERROR、NOT_FOUND 等
数据库错误   (2xxx):  DATABASE_ERROR、DUPLICATE_KEY 等
业务错误     (3xxx):  BUSINESS_ERROR、INVALID_OPERATION 等
外部服务错误 (4xxx):  EXTERNAL_SERVICE_ERROR、TIMEOUT_ERROR 等
```

**服务定义范围示例**（Identity 服务）：
```
认证错误     (5001-5099):  INVALID_CREDENTIALS、TOKEN_EXPIRED 等
用户错误     (5101-5199):  USER_NOT_FOUND、DUPLICATE_USER 等
租户错误     (5201-5299):  TENANT_NOT_FOUND、TENANT_INACTIVE 等
应用错误     (5301-5399):  APPLICATION_NOT_FOUND 等
会话错误     (5401-5499):  SESSION_NOT_FOUND、SESSION_EXPIRED 等
访问密钥错误 (5501-5599):  ACCESS_KEY_NOT_FOUND 等
验证错误     (5601-5699):  VERIFICATION_CODE_INVALID 等
权限错误     (5701-5799):  PERMISSION_DENIED 等
```

### 异常继承和代码的完整规范

**错误代码继承链**：定义错误代码枚举时必须继承 Foundation Kit 的 `ErrorCode`

```python
from aury.boot.application.errors.codes import ErrorCode

# ✅ 正确的继承方式 - 继承 ErrorCode，在 5xxx 范围内定义
class IdentityErrorCode(ErrorCode):
    """Identity 服务错误代码。
    
    继承自 Foundation Kit 的 ErrorCode，在 5xxx 范围内定义。
    不覆盖 Foundation Kit 已有的错误代码（1xxx-4xxx）。
    """
    # 认证错误 (5001-5099)
    INVALID_CREDENTIALS = "5001"
    INVALID_TOKEN = "5002"
    TOKEN_EXPIRED = "5003"
    
    # 用户错误 (5101-5199)
    USER_NOT_FOUND = "5101"
    DUPLICATE_USER = "5104"
    # ... 更多错误代码
```

**异常继承链**：定义异常时必须显式继承 Foundation Kit 的异常类，并在 metadata 中使用错误代码

```python
from aury.boot.application.errors import (
    UnauthorizedError,      # 401
    NotFoundError,          # 404
    AlreadyExistsError,     # 409
    ForbiddenError,         # 403
    ValidationError,        # 400
    BusinessError,          # 400
)

# ✅ 正确的继承方式
class InvalidCredentialsError(UnauthorizedError):
    """凭证无效异常。
    
    继承自 UnauthorizedError (401)
    """
    def __init__(self, message: str = "用户名或密码错误", **kwargs):
        # 必须调用父类 __init__
        metadata = kwargs.pop("metadata", {})
        metadata["error_code"] = IdentityErrorCode.INVALID_CREDENTIALS.value
        super().__init__(message=message, metadata=metadata, **kwargs)

class UserNotFoundError(NotFoundError):
    """用户不存在异常 - 代码 4101"""
    def __init__(self, user_id: str | None = None, **kwargs):
        message = kwargs.pop("message", "用户不存在")
        metadata = kwargs.pop("metadata", {})
        if user_id:
            metadata["user_id"] = user_id
        # 必须调用父类 __init__，传递 resource 和 metadata
        super().__init__(
            message=message, 
            resource="User",
            metadata=metadata, 
            **kwargs
        )

class DuplicateUserError(AlreadyExistsError):
    """用户重复异常 - 代码 4104"""
    def __init__(self, field: str, value: str, **kwargs):
        message = kwargs.pop("message", f"{field} 已被使用")
        metadata = kwargs.pop("metadata", {})
        metadata["field"] = field
        metadata["value"] = value
        # 必须调用父类 __init__
        super().__init__(
            message=message,
            resource="User",
            metadata=metadata,
            **kwargs
        )

# ❌ 错误的方式 - 不继承任何异常
class MyCustomError(Exception):
    pass

# ❌ 错误的方式 - 没有调用父类 __init__
class BadError(NotFoundError):
    def __init__(self, message: str):
        # 没有调用 super().__init__()，会导致异常处理失败
        self.message = message
```

**错误代码追踪示例**：

```python
# 服务层定义异常时使用统一的错误代码
class ErrorCodes:
    """服务错误代码常量"""
    INVALID_CREDENTIALS = 4001      # 认证错误范围
    USER_NOT_FOUND = 4101           # 用户错误范围
    DUPLICATE_USER = 4104
    PERMISSION_DENIED = 4701        # 权限错误范围

# 在异常中使用错误代码（可选）
raise InvalidCredentialsError(
    message="用户名或密码错误",
    metadata={
        "error_code": ErrorCodes.INVALID_CREDENTIALS,
        "timestamp": datetime.utcnow().isoformat(),
    }
)

# HTTP 响应会自动包含元数据中的错误代码
# {
#     "code": 401,                          # HTTP 状态码（由异常类决定）
#     "message": "用户名或密码错误",
#     "metadata": {
#         "error_code": 4001,               # 服务错误代码
#         "timestamp": "2025-12-01T10:00:00"
#     }
# }
```

**继承链要求总结**：

| 要求 | 说明 |
|------|------|
| **必须继承** | 所有异常都必须继承 Foundation Kit 的异常（UnauthorizedError、NotFoundError 等） |
| **调用 super().__init__()** | 必须显式调用父类初始化，传递所有必要参数（message、resource、metadata 等） |
| **不要创建新的基类** | 不要创建自定义的 BaseError 或 AppError，直接继承 Foundation Kit 的异常 |
| **使用 metadata** | 在 metadata 中存储服务特定的错误代码和其他上下文信息 |
| **遵循命名规范** | 使用 `<对象><操作><异常>Error` 格式，例如 `UserNotFoundError` |
| **使用正确的代码范围** | 根据异常类型使用指定的代码范围（4001-4099、4101-4199 等） |

### Identity 服务异常分类示例

Identity 服务按照这一规范定义了异常，展示了正确的继承方式：

#### 认证异常（4001-4099）

```python
from app.constants import (
    InvalidCredentialsError,      # 无效凭证（401）
    InvalidTokenError,             # 无效令牌（401）
    TokenExpiredError,             # 令牌已过期（401）
    SessionExpiredError,           # 会话已过期（401）
    InvalidAccessKeyError,         # 无效访问密钥（401）
)

# 示例：凭证验证失败
if not verify_password(user.password_hash, password):
    raise InvalidCredentialsError("用户名或密码错误")

# 示例：令牌验证失败
try:
    payload = jwt.decode(token, SECRET_KEY)
except jwt.ExpiredSignatureError:
    raise TokenExpiredError()
```

#### 用户异常（4101-4199）

```python
from app.constants import (
    UserNotFoundError,             # 用户不存在（404）
    UserInactiveError,             # 用户未激活（403）
    UserBannedError,               # 用户被禁用（403）
    DuplicateUserError,            # 用户重复（409）
    InvalidPasswordError,          # 无效密码（400）
)

# 示例：用户不存在
user = await user_repo.get(user_id)
if not user:
    raise UserNotFoundError(user_id=user_id)

# 示例：用户状态检查
if user.status == UserStatus.INACTIVE:
    raise UserInactiveError(user_id=user.id)

if user.status == UserStatus.BANNED:
    raise UserBannedError(user_id=user.id)

# 示例：用户重复检查
existing_user = await user_repo.get_by_email(email)
if existing_user:
    raise DuplicateUserError(field="email", value=email)
```

#### 租户异常（4201-4299）

```python
from app.constants import (
    TenantNotFoundError,           # 租户不存在（404）
    TenantInactiveError,           # 租户未激活（403）
)

# 示例：租户不存在
tenant = await tenant_repo.get(tenant_id)
if not tenant:
    raise TenantNotFoundError(tenant_id=tenant_id)

# 示例：租户状态检查
if tenant.status != TenantStatus.ACTIVE:
    raise TenantInactiveError(tenant_id=tenant_id)
```

#### 应用异常（4301-4399）

```python
from app.constants import (
    ApplicationNotFoundError,      # 应用不存在（404）
    ApplicationInactiveError,      # 应用未激活（403）
)

# 示例：应用不存在
app = await app_repo.get(app_id)
if not app:
    raise ApplicationNotFoundError(app_id=app_id)
```

#### 会话异常（4501-4599）

```python
from app.constants import (
    SessionNotFoundError,          # 会话不存在（404）
    SessionExpiredError,           # 会话已过期（401）
)

# 示例：会话验证
session = await session_repo.get(session_id)
if not session:
    raise SessionNotFoundError(session_id=session_id)

if session.expires_at < datetime.utcnow():
    raise SessionExpiredError()
```

#### 访问密钥异常（4401-4499）

```python
from app.constants import (
    AccessKeyNotFoundError,        # 访问密钥不存在（404）
    AccessKeyInactiveError,        # 访问密钥未激活（403）
    AccessKeyRevokedError,         # 访问密钥已撤销（403）
)

# 示例：访问密钥验证
key = await key_repo.get(key_id)
if not key:
    raise AccessKeyNotFoundError(key_id=key_id)

if key.status == AccessKeyStatus.INACTIVE:
    raise AccessKeyInactiveError(key_id=key_id)
```

#### 验证异常（4601-4699）

```python
from app.constants import (
    VerificationCodeInvalidError,  # 验证码无效（400）
    VerificationCodeExpiredError,  # 验证码已过期（400）
    VerificationFailedError,       # 验证失败（400）
)

# 示例：验证码检查
if verification_code != stored_code:
    raise VerificationCodeInvalidError()

if is_expired(verification_time):
    raise VerificationCodeExpiredError()
```

#### 权限异常（4701-4799）

```python
from app.constants import PermissionDeniedError

# 示例：权限检查
if not user_has_permission(user, resource, action):
    raise PermissionDeniedError(resource="User")
```

### Identity 服务异常的继承关系

所有 Identity 服务异常都继承自 Foundation Kit 的基础异常类：

```
Exception (Python)
    ↓
FoundationError (Foundation Kit)
    ↓
BaseError (Foundation Kit 应用异常基类)
    ├── UnauthorizedError (401)
    │   ├── InvalidCredentialsError
    │   ├── InvalidTokenError
    │   ├── TokenExpiredError
    │   ├── SessionExpiredError
    │   └── InvalidAccessKeyError
    │
    ├── ForbiddenError (403)
    │   ├── UserInactiveError
    │   ├── UserBannedError
    │   ├── TenantInactiveError
    │   ├── ApplicationInactiveError
    │   ├── AccessKeyInactiveError
    │   ├── AccessKeyRevokedError
    │   └── PermissionDeniedError
    │
    ├── NotFoundError (404)
    │   ├── UserNotFoundError
    │   ├── TenantNotFoundError
    │   ├── ApplicationNotFoundError
    │   ├── SessionNotFoundError
    │   └── AccessKeyNotFoundError
    │
    ├── AlreadyExistsError (409)
    │   └── DuplicateUserError
    │
    └── ValidationError (400)
        ├── InvalidPasswordError
        ├── VerificationCodeError
        ├── VerificationCodeInvalidError
        ├── VerificationCodeExpiredError
        └── VerificationFailedError
```

### 使用元数据增强异常信息

```python
# 异常可以包含元数据，便于前端识别和处理
raise UserNotFoundError(
    user_id="12345",
    metadata={
        "operation": "read",
        "timestamp": datetime.utcnow().isoformat(),
    }
)

# HTTP 响应示例：
# {
#     "code": 404,
#     "message": "用户不存在",
#     "data": null,
#     "metadata": {
#         "user_id": "12345",
#         "operation": "read",
#         "timestamp": "2025-12-01T10:00:00"
#     }
# }
```

### 在服务层使用异常

```python
from app.constants import (
    UserNotFoundError,
    DuplicateUserError,
    UserInactiveError,
)

class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)
    
    async def get_user(self, user_id: str):
        """获取用户。"""
        user = await self.repo.get(user_id)
        if not user:
            raise UserNotFoundError(user_id=user_id)
        
        if user.status == UserStatus.INACTIVE:
            raise UserInactiveError(user_id=user.id)
        
        return user
    
    async def create_user(self, request: UserCreateRequest):
        """创建用户。"""
        # 检查邮箱是否已被使用
        existing = await self.repo.get_by_email(request.email)
        if existing:
            raise DuplicateUserError(
                field="email",
                value=request.email,
                metadata={"attempted_username": request.username}
            )
        
        # 创建新用户
        user = await self.repo.create({
            "username": request.username,
            "email": request.email,
            "password_hash": hash_password(request.password),
        })
        return user
```

### 在路由层处理异常

```python
from fastapi import APIRouter
from aury.boot.application.interfaces.egress import BaseResponse
from app.constants import UserNotFoundError, DuplicateUserError

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: str, service: UserService = Depends()):
    """获取用户。
    
    Foundation Kit 会自动捕获所有 BaseError 的子类，并转换为标准 HTTP 响应。
    
    抛出的异常：
    - UserNotFoundError → HTTP 404
    - UserInactiveError → HTTP 403
    """
    user = await service.get_user(user_id)
    return BaseResponse(code=200, message="获取成功", data=user)

@router.post("/users")
async def create_user(
    request: UserCreateRequest,
    service: UserService = Depends()
):
    """创建用户。
    
    抛出的异常：
    - DuplicateUserError → HTTP 409
    - InvalidPasswordError → HTTP 400
    """
    user = await service.create_user(request)
    return BaseResponse(code=201, message="用户创建成功", data=user)
```

---

## 异常处理最佳实践

### ✅ 推荐做法

**1. 在适当的层级抛出异常**

```python
# ✅ 好：业务验证在 Service 层
class UserService:
    async def create_user(self, request: UserCreateRequest):
        existing = await self.repo.get_by_email(request.email)
        if existing:
            raise DuplicateUserError(field="email", value=request.email)
        return await self.repo.create({...})

# ❌ 不好：业务验证在 Route 层
@router.post("/users")
async def create_user(request: UserCreateRequest):
    existing = await repo.get_by_email(request.email)
    if existing:
        raise DuplicateUserError(...)
```

**2. 提供有用的元数据**

```python
# ✅ 好
raise UserNotFoundError(
    user_id=user_id,
    metadata={
        "operation": "read",
        "timestamp": datetime.utcnow().isoformat(),
        "requested_by": current_user.id,
    }
)

# ❌ 不好
raise UserNotFoundError(user_id=user_id)
```

**3. 不要创建新的异常基类**

```python
# ✅ 好：继承 Foundation Kit 的异常
from aury.boot.application.errors import NotFoundError

class MyServiceNotFoundError(NotFoundError):
    pass

# ❌ 错：创建新的异常基类
class MyServiceBaseError(Exception):
    pass

class MyServiceNotFoundError(MyServiceBaseError):
    pass
```

**4. 让 Foundation Kit 处理异常转换**

```python
# ✅ 好：异常由 Foundation Kit 全局处理器处理
@router.get("/users/{user_id}")
async def get_user(user_id: str, service: UserService = Depends()):
    user = await service.get_user(user_id)  # 可能抛出异常
    return BaseResponse(code=200, message="获取成功", data=user)

# ❌ 不好：手动处理异常转换
@router.get("/users/{user_id}")
async def get_user(user_id: str, service: UserService = Depends()):
    try:
        user = await service.get_user(user_id)
        return BaseResponse(code=200, message="获取成功", data=user)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
```

### ❌ 常见错误

**错误 1：不继承 Foundation Kit 异常**

```python
# ❌ 错
class MyAppError(Exception):
    pass

# Foundation Kit 不会捕获这个异常，导致 500 错误
raise MyAppError("出错了")
```

**错误 2：捕获异常后吞掉**

```python
# ❌ 错
try:
    user = await get_user(user_id)
except UserNotFoundError:
    pass  # 吞掉异常，导致后续错误

# ✅ 好
try:
    user = await get_user(user_id)
except UserNotFoundError as e:
    logger.warning(f"User not found: {user_id}")
    raise  # 重新抛出异常
```

**错误 3：异常消息格式不一致**

```python
# ❌ 不好：消息格式混乱
raise UserNotFoundError("user is not exist")
raise UserNotFoundError("用户不存在")
raise UserNotFoundError("找不到用户")

# ✅ 好：统一的消息格式
raise UserNotFoundError(user_id=user_id)  # 使用默认消息
# 输出：用户不存在
```

**错误 4：使用错误的异常类型**

```python
# ❌ 错
raise NotFoundError("用户已过期")  # 用户过期不是"不存在"

# ✅ 好
raise UserInactiveError(user_id=user_id)  # 使用专门的异常
```

---

## 异常处理清单

集成新服务时的异常处理检查清单：

- [ ] 所有业务异常都继承 Foundation Kit 的异常类
- [ ] 异常命名遵循 `<对象><操作><异常>Error` 格式
- [ ] 异常代码使用服务指定的范围
- [ ] Service 层负责业务验证并抛出异常
- [ ] Route 层不进行异常转换处理（由 Foundation Kit 处理）
- [ ] 异常包含有用的元数据
- [ ] 异常消息格式统一，支持国际化
- [ ] 不存在自定义的异常基类体系

---

## 下一步

- 查看 [10-transaction-management.md](./10-transaction-management.md) 了解事务管理和异常处理的结合
- 查看 [07-http-advanced.md](./07-http-advanced.md) 了解响应模型
- 查看 [22-best-practices.md](./22-best-practices.md) 了解整体架构最佳实践

