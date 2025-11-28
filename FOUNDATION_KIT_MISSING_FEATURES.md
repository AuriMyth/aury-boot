# Foundation Kit 功能对比分析

## 🎯 文档目标

全面对比 AuriMyth Foundation Kit 与主流顶级框架的功能差距，明确：
- ✅ **真实差距**：顶级框架原生提供，Kit 缺失的功能
- ✅ **企业级通用需求**：所有框架都需要第三方支持的功能
- ✅ **Core 层优化**：框架核心能力的深度优化建议

**对比框架**：
- **Python**: Django, Flask, FastAPI
- **Java**: Spring Boot
- **PHP**: Laravel
- **Ruby**: Rails
- **Node.js**: NestJS, Express

---

## 📊 功能对比总览表

| 功能模块 | Django | Spring Boot | Laravel | Rails | FastAPI | NestJS | **Kit** | 差距类型 |
|---------|--------|------------|---------|-------|---------|--------|---------|---------|
| **核心框架** |
| 路由系统 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | - |
| 中间件 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | - |
| 依赖注入 | ⚠️ 基础 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | - |
| 组件化架构 | ✅ Apps | ✅ Beans | ✅ Service Providers | ✅ Engines | ❌ 需第三方 | ✅ Modules | ✅ Components | - |
| **数据访问** |
| ORM | ✅ Django ORM | ✅ JPA/Hibernate | ✅ Eloquent | ✅ ActiveRecord | ❌ 需第三方 | ✅ TypeORM | ⚠️ SQLAlchemy（绑定） | 🔴 需抽象 |
| 数据库迁移 | ✅ 原生 | ✅ Flyway/Liquibase | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ TypeORM | ✅ 原生（完整） | - |
| 事务管理 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | - |
| Repository 模式 | ❌ 需第三方 | ✅ JPA Repository | ❌ 需第三方 | ✅ ActiveRecord | ❌ 需第三方 | ✅ TypeORM | ⚠️ 原生（绑定 SQLAlchemy） | 🔴 需抽象 |
| **测试框架** |
| 测试基类 | ✅ TestCase | ✅ @SpringBootTest | ✅ TestCase | ✅ Test::Unit | ❌ 需第三方 | ✅ TestingModule | ⚠️ 基础 | 🔴 增强 |
| 测试客户端 | ✅ Client | ✅ TestRestTemplate | ✅ TestCase | ✅ IntegrationTest | ✅ TestClient | ✅ TestingModule | ✅ TestClient | - |
| Fixtures | ✅ 原生 | ✅ @Sql | ✅ Factories | ✅ Fixtures | ❌ 需第三方 | ✅ TestingModule | ⚠️ Factory | 🟡 增强 |
| 数据库回滚 | ✅ 自动 | ✅ @Transactional | ✅ DatabaseTransactions | ✅ 自动 | ❌ 需第三方 | ✅ TestingModule | ✅ 自动 | - |
| **国际化** |
| i18n/l10n | ✅ 原生 | ✅ MessageSource | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ i18n | ✅ 原生 | - |
| 时区处理 | ✅ 原生 | ✅ TimeZone | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ⚠️ 基础（参数未实现） | 🟡 增强 |
| **安全认证** |
| 认证系统 | ✅ 原生 | ✅ Spring Security | ✅ 原生 | ✅ Devise | ❌ 需第三方 | ✅ Passport | ⚠️ 用户服务 | - |
| 授权系统 | ✅ Permissions | ✅ @PreAuthorize | ✅ Policies | ✅ CanCan | ❌ 需第三方 | ✅ Guards | ⚠️ 用户服务 | - |
| 密码加密 | ✅ 原生 | ✅ BCrypt | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ⚠️ Passlib | 🟡 集成 |
| JWT 支持 | ❌ 需第三方 | ✅ Spring Security | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ⚠️ PyJWT | 🟡 集成 |
| **可观测性** |
| 健康检查 | ❌ 需第三方 | ✅ Actuator | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ⚠️ 基础 | 🔴 增强 |
| 指标收集 | ❌ 需第三方 | ✅ Actuator | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ❌ 缺失 | 🔴 高 |
| 分布式追踪 | ❌ 需第三方 | ✅ Sleuth | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ❌ 缺失 | 🔴 高 |
| 日志系统 | ✅ 原生 | ✅ Logback | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ✅ Loguru | - |
| **安全合规** |
| 请求限流 | ❌ 需第三方 | ✅ RateLimiter | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ⚠️ 网关层 | - |
| API Key 管理 | ❌ 需第三方 | ✅ Spring Security | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ❌ 缺失 | 🔴 高 |
| CORS | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | ✅ 原生 | - |
| 数据脱敏 | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ❌ 缺失 | 🟡 中 |
| **配置管理** |
| 环境配置 | ✅ Settings | ✅ application.yml | ✅ .env | ✅ config/ | ✅ Pydantic | ✅ ConfigModule | ✅ Pydantic | - |
| 多环境支持 | ✅ 原生 | ✅ Profiles | ✅ 原生 | ✅ 原生 | ⚠️ 需配置 | ✅ 原生 | ⚠️ 需配置 | 🟡 增强 |
| 密钥管理 | ❌ 需第三方 | ✅ Vault | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ ConfigModule | ❌ 缺失 | 🟡 中 |
| **任务调度** |
| 定时任务 | ❌ 需第三方 | ✅ @Scheduled | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ @Cron | ✅ APScheduler | - |
| 异步任务 | ❌ Celery | ✅ @Async | ❌ Queue | ❌ Sidekiq | ❌ Celery | ✅ Bull | ✅ Dramatiq | - |
| **缓存** |
| 缓存抽象 | ✅ 原生 | ✅ Cache Abstraction | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ CacheModule | ✅ 原生 | - |
| 多后端支持 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | - |
| **存储** |
| 对象存储 | ❌ 需第三方 | ❌ 需第三方 | ✅ Storage | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ S3 | - |
| **事件系统** |
| 事件总线 | ❌ 需第三方 | ✅ ApplicationEvent | ✅ 原生 | ✅ 原生 | ❌ 需第三方 | ✅ EventEmitter | ✅ 原生 | - |
| **RPC 通信** |
| RPC 框架 | ❌ 需第三方 | ✅ Feign | ❌ 需第三方 | ❌ 需第三方 | ❌ 需第三方 | ✅ 原生 | ✅ 原生 | - |

**图例**：
- ✅ 原生支持
- ⚠️ 基础支持（需增强）
- ❌ 缺失或需第三方
- 🔴 高优先级差距
- 🟡 中优先级差距

---

## 🔴 第一部分：真实差距（顶级框架原生提供，Kit 缺失）

### 概述

这些功能在**至少 3 个顶级框架中都有原生支持**，但 Foundation Kit 缺失。这是 Kit 与顶级框架的真实差距。

---

### 1. **认证和授权系统** ⭐⭐⭐⭐⭐

#### 架构说明：
- **Kit 设计**：采用微服务架构，认证授权由独立的**用户服务**提供（类似 Spring Cloud）
- **其他框架**：单体应用，认证授权内置在框架中

#### 顶级框架支持情况：
- **Django**: ✅ `django.contrib.auth` - 完整的认证授权系统（单体应用）
- **Spring Boot**: ✅ `Spring Security` - 企业级安全框架（单体应用）
- **Spring Cloud**: ⚠️ 用户服务 - 认证授权由独立服务提供（微服务架构）
- **Laravel**: ✅ `Auth` + `Policies` - 完整的认证授权（单体应用）
- **Rails**: ✅ `Devise` + `CanCan` - 认证授权 Gem（单体应用）
- **NestJS**: ✅ `Passport` + `Guards` - 完整的认证授权（单体应用）
- **FastAPI**: ❌ 需第三方（`fastapi-users`, `python-jose`）

#### Kit 现状：
- ⚠️ **由用户服务提供**（微服务架构设计）
- Foundation Kit 不包含认证授权系统
- 认证授权由独立的用户服务（User Service）提供
- 通过 RPC 或 API 调用用户服务进行认证授权

#### 架构优势：
- ✅ 服务解耦：认证授权独立部署和扩展
- ✅ 统一管理：所有服务共享同一认证授权服务
- ✅ 灵活扩展：可以替换不同的认证授权实现
- ✅ 符合微服务架构最佳实践

#### 使用方式：
```python
# 通过 RPC 调用用户服务
from aurimyth.foundation_kit.application.rpc import RPCClient

rpc_client = RPCClient("user-service")

# 验证 Token
user = await rpc_client.call("auth.verify_token", token=token)

# 检查权限
has_permission = await rpc_client.call("auth.check_permission", 
                                       user_id=user.id, 
                                       permission="user.create")
```

**结论**：✅ **设计决策**，不是缺失功能。Kit 采用微服务架构，认证授权由用户服务提供，符合 Spring Cloud 等微服务框架的设计理念。

---

### 2. **可观测性（Observability）** ⭐⭐⭐⭐⭐

#### 顶级框架支持情况：
- **Spring Boot**: ✅ `Actuator` - 完整的监控和健康检查
- **NestJS**: ✅ 原生支持 - 健康检查、指标、追踪
- **Django**: ❌ 需第三方（`django-health-check`, `django-prometheus`）
- **Laravel**: ❌ 需第三方（`laravel-health`）
- **Rails**: ❌ 需第三方
- **FastAPI**: ❌ 需第三方

#### Kit 现状：
- ⚠️ **基础支持**（只有简单的健康检查）
- ❌ 无指标收集（Prometheus）
- ❌ 无分布式追踪（OpenTelemetry）
- ❌ 无性能监控

#### 影响：
- 生产环境难以监控
- 无法追踪性能瓶颈
- 难以定位分布式系统问题

#### 建议补充：

##### 2.1 健康检查增强
```python
# 应该提供
from aurimyth.foundation_kit.observability.health import health_check, HealthStatus

@router.get("/health")
async def health():
    return await health_check({
        "database": check_database,
        "cache": check_cache,
        "storage": check_storage,
        "external_api": check_external_api,
    })
```

##### 2.2 指标收集（Prometheus）
```python
# 应该提供
from aurimyth.foundation_kit.observability.metrics import MetricsCollector

metrics = MetricsCollector()
metrics.increment("http.requests", tags={"method": "GET", "status": "200"})
metrics.histogram("http.duration", duration_ms, tags={"endpoint": "/users"})
metrics.gauge("active.connections", count)
```

##### 2.3 分布式追踪（OpenTelemetry）
```python
# 应该提供
from aurimyth.foundation_kit.observability.tracing import trace

@trace("user_service.create_user")
async def create_user(data):
    # 自动注入 trace context
    pass
```

**优先级**：🔴 **极高**（企业级应用必需，生产环境监控）

---

### 3. **安全合规（Security & Compliance）** ⭐⭐⭐⭐⭐

#### 架构说明：
- **限流**：应该在**网关层**（API Gateway）实现，而不是应用层
- **API Key 管理**：可以在网关层或应用层实现
- **数据脱敏**：应用层功能，用于响应数据脱敏

#### 顶级框架支持情况：
- **Spring Boot**: ✅ `RateLimiter` - Spring Security 提供（应用层）
- **Spring Cloud Gateway**: ✅ 网关层限流（推荐）
- **NestJS**: ✅ 原生支持 - 限流、API Key（应用层）
- **Kong/Envoy**: ✅ 网关层限流（微服务架构推荐）
- **Django**: ❌ 需第三方（`django-ratelimit`）
- **Laravel**: ❌ 需第三方（`laravel-rate-limiter`）
- **Rails**: ❌ 需第三方
- **FastAPI**: ❌ 需第三方

#### Kit 现状：
- ⚠️ **限流由网关层提供**（架构设计决策）
- ⚠️ **API Key 管理**：可由网关层或用户服务提供
- ❌ 无数据脱敏工具

#### 架构设计：

##### 3.1 请求限流（网关层）

**设计决策**：
- 限流应该在**API Gateway**层实现，而不是应用层
- 优势：
  - 统一限流策略：所有服务共享同一限流规则
  - 性能优化：在网关层拦截，减少后端服务压力
  - 集中管理：限流规则集中配置和管理
  - 分布式限流：网关层更容易实现分布式限流

**网关层限流方案**：
- 使用 **Kong**、**Envoy**、**Traefik** 等 API Gateway
- 或使用 **Nginx** + **lua-resty-limit-traffic**
- 或自建网关服务（使用 Foundation Kit 构建）

**应用层限流（可选补充）**：
- 可作为网关限流的补充
- 用于细粒度限流（如特定接口限流）
- 用于网关不可用时的降级方案

##### 3.2 API Key 管理

**设计决策**：
- 可以在网关层或应用层实现
- 推荐：网关层统一验证，应用层可选择性验证

**方案一：网关层验证（推荐）**
- API Gateway 统一验证 API Key
- 验证通过后转发请求到后端服务
- 后端服务无需关心 API Key 验证

**方案二：应用层验证**
- 每个服务自己验证 API Key
- 通过中间件或装饰器实现
- 适合需要细粒度控制的场景

**方案三：用户服务验证（推荐，与认证统一）**
- API Key 验证由用户服务提供
- 网关层或应用层调用用户服务验证
- 与认证授权统一管理

##### 3.3 数据脱敏

**设计**：
- 应用层功能，用于响应数据脱敏
- 提供工具函数，不依赖外部服务

**建议补充**：
```python
# 应该提供
from aurimyth.foundation_kit.security.masking import mask_phone, mask_email, mask_id_card

masked = mask_phone("13800138000")  # "138****8000"
masked = mask_email("user@example.com")  # "u***@example.com"
masked = mask_id_card("110101199001011234")  # "110101********1234"
```

**优先级**：
- **限流**：✅ 由网关层提供（架构设计）
- **API Key**：🟡 中优先级（可由网关层或用户服务提供）
- **数据脱敏**：🟡 中优先级（应用层工具）

---

### 4. **测试框架增强** ⭐⭐⭐⭐

#### 顶级框架支持情况：
- **Django**: ✅ `TestCase`, `Fixtures` - 完整的测试框架
- **Spring Boot**: ✅ `@SpringBootTest`, `@Sql` - 完整的测试支持
- **Laravel**: ✅ `TestCase`, `Factories` - 完整的测试框架
- **Rails**: ✅ `Test::Unit`, `Fixtures` - 完整的测试框架
- **NestJS**: ✅ `TestingModule` - 完整的测试支持
- **FastAPI**: ⚠️ 需第三方（`pytest`, `httpx`）

#### Kit 现状：
- ⚠️ **基础支持**
- ✅ 有 `TestCase` 基类
- ✅ 有 `TestClient`
- ⚠️ `Factory` 功能有限
- ❌ 无 Fixtures 支持

#### 影响：
- 测试编写不够便捷
- 缺少测试数据管理工具

#### 建议补充：
```python
# 应该提供
from aurimyth.foundation_kit.testing import TestCase, TestClient, Factory, Fixtures

class UserServiceTest(TestCase):
    fixtures = ["users.json", "roles.json"]  # 自动加载 Fixtures
    
    async def setUp(self):
        self.client = TestClient(app)
        self.user_factory = Factory(User)
    
    async def test_create_user(self):
        # Factory 支持关联创建
        user = await self.user_factory.create(
            name="张三",
            profile__bio="简介",  # 自动创建关联对象
        )
        assert user.profile.bio == "简介"
```

**优先级**：🟡 **高**（提高开发效率，减少学习成本）

---

### 5. **数据库迁移工具** ⭐⭐⭐⭐

#### 顶级框架支持情况：
- **Django**: ✅ `makemigrations`, `migrate` - 便捷的命令行工具
- **Laravel**: ✅ `php artisan migrate` - 便捷的命令行工具
- **Rails**: ✅ `rails db:migrate` - 便捷的命令行工具
- **Spring Boot**: ⚠️ Flyway/Liquibase（需配置）
- **NestJS**: ✅ TypeORM Migration（便捷）
- **FastAPI**: ❌ Alembic（需手动管理）

#### Kit 现状：
- ✅ **完整支持**（已实现）
- ✅ 有完整的命令行工具（`aurimyth-migrate`）
- ✅ 支持所有核心功能：
  - `make` - 生成迁移文件（自动检测模型变更）
  - `up` - 执行迁移
  - `down` - 回滚迁移
  - `status` - 查看迁移状态
  - `show` - 显示所有迁移（Rich 表格）
  - `check` - 检查迁移文件
  - `merge` - 合并迁移分支
  - `history` - 显示迁移历史
- ✅ 支持干运行（dry-run）
- ✅ 支持自动生成（autogenerate）
- ✅ 使用 Rich 进行可视化输出

#### 已实现功能：
```bash
# 生成迁移
aurimyth-migrate make -m "add user table"

# 执行迁移
aurimyth-migrate up

# 回滚迁移
aurimyth-migrate down previous

# 查看状态
aurimyth-migrate status

# 显示所有迁移（Rich 表格）
aurimyth-migrate show

# 检查迁移
aurimyth-migrate check

# 合并迁移
aurimyth-migrate merge "abc123,def456"

# 显示历史
aurimyth-migrate history
```

#### 可选增强（非必需）：
- ⚠️ 迁移前备份（可选功能）
- ⚠️ 迁移回滚确认（安全提示）
- ⚠️ 迁移性能分析（执行时间统计）

**结论**：✅ **已完整实现**，功能与 Django/Laravel 相当，无需补充

---

## 🟡 第二部分：企业级通用需求（所有框架都需要第三方支持）

### 概述

这些功能**所有框架都需要第三方库支持**，不是 Kit 相对于其他框架的差距，而是**企业级应用的通用需求**。

---

### 1. **配置管理增强** ⭐⭐⭐⭐

#### 所有框架现状：
- **Django**: ⚠️ 基础（`settings.py`），需 `django-environ` 增强
- **Spring Boot**: ✅ 原生（`application.yml`）
- **Laravel**: ⚠️ 基础（`.env`），需 `config` 增强
- **Rails**: ⚠️ 基础（`config/`），需 `figaro` 增强
- **NestJS**: ✅ 原生（`ConfigModule`）
- **FastAPI**: ⚠️ 基础（Pydantic Settings）

#### Kit 现状：
- ⚠️ **基础支持**（Pydantic Settings）
- ✅ 支持环境变量和 `.env` 文件
- ❌ 缺少多环境配置管理（dev/staging/prod）
- ❌ 缺少密钥管理（Vault、AWS Secrets Manager 等）

#### 设计方案：

##### 1.1 多环境配置架构

**设计目标**：
- 支持多环境（development、staging、production）
- 配置文件分层（base + environment-specific）
- 配置优先级：环境变量 > 环境配置文件 > base 配置文件 > 默认值
- 配置合并策略：深度合并，环境配置覆盖 base 配置

**目录结构**：
```
config/
├── base.yaml              # 基础配置（所有环境共享）
├── development.yaml       # 开发环境配置
├── staging.yaml           # 预发布环境配置
├── production.yaml        # 生产环境配置
└── secrets/               # 密钥配置（不提交到 Git）
    ├── development.yaml
    ├── staging.yaml
    └── production.yaml
```

**配置加载顺序**：
1. 加载 `base.yaml`（基础配置）
2. 加载环境配置文件（如 `production.yaml`），覆盖 base 配置
3. 加载环境变量，覆盖文件配置
4. 加载密钥（从 Vault 或 secrets 文件），覆盖所有配置

**环境变量控制**：
- `ENV` 或 `ENVIRONMENT`：指定环境（development/staging/production）
- `CONFIG_DIR`：配置文件目录（默认 `config/`）

##### 1.2 密钥管理架构

**架构设计决策**：
- **框架内**：提供密钥管理接口和基础实现（环境变量、本地文件）
- **插件**：高级密钥管理（Vault、AWS Secrets Manager）作为独立插件

**设计理由**：
1. **保持框架轻量**：不是所有项目都需要 Vault/AWS
2. **灵活扩展**：不同项目可以选择不同的密钥管理方案
3. **符合插件化设计**：基础设施集成应该作为插件
4. **参考最佳实践**：Spring Cloud Vault、django-vault 都是独立项目

**框架内提供（核心）**：
1. **SecretManager 接口**（抽象层）
   - 定义密钥获取接口
   - 支持多种实现
   
2. **环境变量密钥源**（基础实现）
   - 简单直接
   - 适合本地开发
   - 格式：`SECRET_<KEY_NAME>`

3. **本地密钥文件**（基础实现）
   - `config/secrets/<env>.yaml`
   - 可选加密存储（使用 Fernet）
   - 不提交到 Git

**插件提供（可选）**：
1. **Vault 插件**（`aurimyth-foundation-kit-vault`）
   - 集成 HashiCorp Vault
   - 支持动态密钥
   - 支持密钥轮换
   - 支持审计日志

2. **AWS Secrets Manager 插件**（`aurimyth-foundation-kit-aws-secrets`）
   - 集成 AWS Secrets Manager
   - 与 AWS 服务集成
   - 自动加密
   - 版本管理

3. **其他密钥源插件**（按需扩展）
   - Azure Key Vault
   - Google Secret Manager
   - 自定义密钥源

**密钥配置示例**：
```yaml
# config/secrets/production.yaml（加密）
database:
  password: "encrypted:gAAAAABh..."  # 加密后的密码

redis:
  password: "encrypted:gAAAAABh..."

api_keys:
  third_party_api: "encrypted:gAAAAABh..."
```

**密钥注入机制**：
- 配置类中标记需要密钥的字段（使用 `SecretField`）
- 配置加载时自动从密钥源获取并注入
- 支持密钥引用（`${vault:database/password}`）

##### 1.3 配置管理器设计

**ConfigManager 职责**：
1. 环境检测（从环境变量或配置文件）
2. 配置文件加载和合并
3. 密钥获取和注入
4. 配置验证（Pydantic）
5. 配置缓存（避免重复加载）

**配置合并策略**：
- 深度合并（deep merge）
- 列表合并策略：环境配置替换 base 配置（不合并）
- 字典合并策略：环境配置覆盖 base 配置的对应键

**配置验证**：
- 使用 Pydantic 进行类型验证
- 必需字段检查
- 配置值范围检查（如端口范围）
- 配置依赖检查（如数据库 URL 格式）

##### 1.4 使用方式设计

**方式一：环境变量控制（推荐）**
```bash
# 设置环境
export ENV=production
export VAULT_ADDR=https://vault.example.com
export VAULT_TOKEN=xxx

# 应用自动加载配置
python main.py
```

**方式二：代码中指定**
```python
from aurimyth.foundation_kit.config import ConfigManager
from aurimyth.foundation_kit.config.secrets import FileSecretManager

# 使用框架内的文件密钥源
config = ConfigManager(
    env="production",
    config_dir="config",
    secret_manager=FileSecretManager(encrypted=True),
)

# 或使用 Vault 插件
from aurimyth_foundation_kit_vault import VaultSecretManager

config = ConfigManager(
    env="production",
    secret_manager=VaultSecretManager(
        vault_addr="https://vault.example.com",
    ),
)
```

**方式三：继承 BaseConfig**
```python
from aurimyth.foundation_kit.application.config import BaseConfig

# 自动检测环境并加载配置
config = BaseConfig()  # 从 ENV 环境变量获取环境
```

##### 1.5 配置文件格式

**YAML 格式（推荐）**：
```yaml
# config/base.yaml
database:
  host: "localhost"
  port: 5432
  pool_size: 5

cache:
  type: "redis"
  max_size: 1000

# config/production.yaml
database:
  host: "prod-db.example.com"
  pool_size: 20  # 覆盖 base 配置

cache:
  type: "redis"
  redis_url: "${secret:cache/redis_url}"  # 从密钥管理器获取（框架统一接口）
```

**环境变量格式**：
```bash
# .env
ENV=development
DATABASE_HOST=localhost
DATABASE_PORT=5432

# 密钥（开发环境）
SECRET_DATABASE_PASSWORD=dev_password
```

##### 1.6 密钥管理实现细节

**框架内实现（核心）**：

**SecretManager 接口**：
```python
# 框架提供接口
class SecretManager(ABC):
    @abstractmethod
    async def get_secret(self, key: str) -> str:
        """获取密钥"""
        pass
    
    @abstractmethod
    async def get_secrets(self, prefix: str) -> dict[str, str]:
        """批量获取密钥"""
        pass
```

**环境变量密钥源**：
- 实现 `EnvironmentSecretManager`
- 从环境变量读取（`SECRET_<KEY_NAME>`）
- 无需额外依赖

**本地文件密钥源**：
- 实现 `FileSecretManager`
- 从 `config/secrets/<env>.yaml` 读取
- 可选加密（使用 `cryptography` 库）
- 开发环境可选项（不强制加密）

**插件实现（可选）**：

**Vault 插件**（`aurimyth-foundation-kit-vault`）：
- 使用 `hvac` 库连接 Vault
- 支持 KV v1 和 KV v2
- 支持动态密钥（如数据库凭证）
- 支持密钥轮换监听
- 实现 `VaultSecretManager`

**AWS Secrets Manager 插件**（`aurimyth-foundation-kit-aws-secrets`）：
- 使用 `boto3` 连接 AWS
- 支持区域选择
- 支持密钥版本管理
- 支持自动刷新
- 实现 `AWSSecretManager`

##### 1.7 配置热重载（可选）

**设计**：
- 监听配置文件变化
- 支持配置热重载（不重启应用）
- 配置变更事件通知
- 组件自动响应配置变更

**使用场景**：
- 开发环境：自动重载配置
- 生产环境：手动触发重载（通过 API）

##### 1.8 配置验证和错误处理

**验证规则**：
- 类型验证（Pydantic）
- 必需字段检查
- 值范围检查（端口、超时等）
- 格式验证（URL、邮箱等）
- 依赖检查（如数据库 URL 格式）

**错误处理**：
- 配置文件不存在：使用默认配置或抛出明确错误
- 密钥获取失败：抛出明确错误，不静默失败
- 配置验证失败：列出所有验证错误
- 配置合并冲突：记录警告，使用优先级高的配置

##### 1.9 实施计划

**阶段一：多环境配置（框架内）**
1. 实现 `ConfigManager` 类
2. 支持 YAML 配置文件加载
3. 实现配置合并逻辑
4. 支持环境变量控制

**阶段二：密钥管理基础（框架内）**
1. 实现 `SecretManager` 接口（抽象层）
2. 实现 `EnvironmentSecretManager`（环境变量）
3. 实现 `FileSecretManager`（本地文件）
4. 实现密钥注入机制
5. 支持密钥引用（`${secret:database/password}`）

**阶段三：Vault 插件（独立插件包）**
1. 创建 `aurimyth-foundation-kit-vault` 插件包
2. 实现 `VaultSecretManager`
3. 集成 HashiCorp Vault
4. 支持动态密钥和密钥轮换

**阶段四：AWS Secrets Manager 插件（独立插件包）**
1. 创建 `aurimyth-foundation-kit-aws-secrets` 插件包
2. 实现 `AWSSecretManager`
3. 集成 AWS Secrets Manager
4. 支持区域和版本管理

**插件使用方式**：
```python
# 安装插件
pip install aurimyth-foundation-kit-vault

# 使用插件
from aurimyth_foundation_kit_vault import VaultSecretManager

config = ConfigManager(
    env="production",
    secret_manager=VaultSecretManager(
        vault_addr="https://vault.example.com",
        vault_token="xxx",
    ),
)
```

**优先级**：🟡 **高**（多环境部署必需）

---

## 🔵 第三部分：Core 层深度优化（框架核心能力增强）

### 概述

这些优化任务旨在提升 Core 层（Models、Repository、Service）的健壮性、性能和易用性。这些不是"缺失功能"，而是"深度优化"。

详细任务清单请参考：`CORE_LAYER_OPTIMIZATION_TODO.md`

---

### 1. **模型基类优化** ⭐⭐⭐⭐

#### 当前问题：
- ⚠️ `datetime.utcnow` 已弃用（Python 3.12+）
- ⚠️ 软删除机制不够灵活（只有 `yn` 字段）
- ⚠️ 缺少 UUID 主键支持
- ⚠️ 缺少版本控制（乐观锁）

#### 建议补充：

##### 1.1 修复时间戳字段
```python
# 修复前
created_at = Column(DateTime, default=datetime.utcnow)  # ❌ 已弃用

# 修复后
from sqlalchemy import func
created_at = Column(DateTime, server_default=func.now())  # ✅ 推荐
```

##### 1.2 软删除机制扩展
```python
# 应该提供
from aurimyth.foundation_kit.core.models import SoftDeleteModel

class User(SoftDeleteModel):
    # 自动包含 deleted_at 字段
    pass

# Repository 支持
await repo.soft_delete(user)  # 设置 deleted_at
await repo.hard_delete(user)   # 物理删除
```

##### 1.3 UUID 主键支持
```python
# 应该提供
from aurimyth.foundation_kit.core.models import UUIDModel

class User(UUIDModel):
    # 自动使用 UUID 主键
    pass
```

##### 1.4 版本控制（乐观锁）
```python
# 应该提供
from aurimyth.foundation_kit.core.models import VersionedModel

class User(VersionedModel):
    # 自动包含 version 字段
    pass

# Repository 自动检查版本
await repo.update(user, data)  # 如果 version 不匹配，抛出 StaleObjectError
```

**优先级**：🔴 **高**（核心功能修复）

---

### 2. **ORM 可扩展性** ⭐⭐⭐⭐⭐

#### 当前问题：
- ⚠️ **ORM 依赖过死**，直接绑定 SQLAlchemy
- ⚠️ `BaseModel` 直接继承 SQLAlchemy 的 `declarative_base()`
- ⚠️ `BaseRepository` 直接使用 `AsyncSession`、`Select` 等 SQLAlchemy 类型
- ⚠️ `BaseService` 直接使用 `AsyncSession`
- ⚠️ 无法替换为其他 ORM（如 Tortoise ORM、Peewee、SQLModel 等）

#### 顶级框架对比：
- **Spring Boot**: ✅ JPA 抽象层，支持 Hibernate、EclipseLink 等多种实现
- **Django**: ⚠️ 绑定 Django ORM，但提供数据库路由支持多数据库
- **Laravel**: ⚠️ 绑定 Eloquent，但提供查询构建器抽象
- **Rails**: ⚠️ 绑定 ActiveRecord，但提供数据库适配器抽象
- **NestJS**: ✅ TypeORM 抽象，支持多种 ORM（TypeORM、Sequelize、Prisma）

#### 影响：
- 无法根据项目需求选择最适合的 ORM
- 迁移到其他 ORM 需要大量重构
- 测试时无法使用轻量级 ORM（如 InMemory ORM）
- 多数据库支持困难

#### 建议补充：

##### 2.1 ORM 抽象层
```python
# 应该提供 ORM 抽象接口
from aurimyth.foundation_kit.core.orm import ORMAdapter, Session, Query

# ORM 适配器接口
class ORMAdapter(ABC):
    """ORM 适配器抽象接口。"""
    
    @abstractmethod
    def create_session(self) -> Session:
        """创建数据库会话。"""
        pass
    
    @abstractmethod
    def create_query(self, model_class) -> Query:
        """创建查询对象。"""
        pass

# SQLAlchemy 实现
class SQLAlchemyAdapter(ORMAdapter):
    """SQLAlchemy ORM 适配器。"""
    def create_session(self) -> SQLAlchemySession:
        pass

# Tortoise ORM 实现
class TortoiseAdapter(ORMAdapter):
    """Tortoise ORM 适配器。"""
    def create_session(self) -> TortoiseSession:
        pass
```

##### 2.2 模型基类抽象
```python
# 应该提供 ORM 无关的模型基类
from aurimyth.foundation_kit.core.models import BaseModel, ModelMeta

class BaseModel(ABC):
    """ORM 无关的模型基类。"""
    
    @classmethod
    @abstractmethod
    def get_orm_adapter(cls) -> ORMAdapter:
        """获取 ORM 适配器。"""
        pass

# SQLAlchemy 实现
class SQLAlchemyModel(BaseModel):
    """SQLAlchemy 模型基类。"""
    __orm_adapter__ = SQLAlchemyAdapter()
    
    # 使用 SQLAlchemy 定义
    id = Column(Integer, primary_key=True)

# Tortoise ORM 实现
class TortoiseModel(BaseModel):
    """Tortoise ORM 模型基类。"""
    __orm_adapter__ = TortoiseAdapter()
    
    # 使用 Tortoise ORM 定义
    id = fields.IntField(pk=True)
```

##### 2.3 Repository 抽象
```python
# 应该提供 ORM 无关的 Repository
from aurimyth.foundation_kit.core.repository import BaseRepository, Session

class BaseRepository(IRepository[ModelType]):
    """ORM 无关的 Repository 基类。"""
    
    def __init__(self, session: Session, model_class: type[ModelType]) -> None:
        """初始化 Repository。
        
        Args:
            session: ORM 无关的会话接口
            model_class: 模型类
        """
        self._session = session
        self._model_class = model_class
        self._orm_adapter = model_class.get_orm_adapter()
    
    async def get(self, id: int) -> ModelType | None:
        """根据ID获取实体（ORM 无关）。"""
        query = self._orm_adapter.create_query(self._model_class)
        return await query.filter(id=id).first()
```

##### 2.4 配置化 ORM 选择
```python
# 应该支持配置化选择 ORM
from aurimyth.foundation_kit.application.config import BaseConfig

class DatabaseSettings(BaseConfig):
    orm_type: str = "sqlalchemy"  # 或 "tortoise", "peewee", "sqlmodel"
    sqlalchemy_url: str | None = None
    tortoise_config: dict | None = None
```

##### 2.5 多 ORM 支持示例
```python
# 使用 SQLAlchemy
from aurimyth.foundation_kit.core.models.sqlalchemy import SQLAlchemyModel

class User(SQLAlchemyModel):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)

# 使用 Tortoise ORM
from aurimyth.foundation_kit.core.models.tortoise import TortoiseModel

class User(TortoiseModel):
    id = fields.IntField(pk=True)

# Repository 自动适配
repo = UserRepository(session)  # 自动使用对应的 ORM 适配器
```

**优势**：
- ✅ 可以替换 ORM（SQLAlchemy、Tortoise ORM、Peewee、SQLModel）
- ✅ 测试时可以使用轻量级 ORM
- ✅ 支持多数据库（不同模型使用不同 ORM）
- ✅ 更好的可测试性（可以 Mock ORM 层）

**优先级**：🔴 **高**（提升框架灵活性和可扩展性）

---

### 3. **Repository 模式增强** ⭐⭐⭐⭐⭐

#### 当前问题：
- ⚠️ 查询构建器功能有限（只支持等值查询）
- ⚠️ 批量操作性能不佳
- ⚠️ 缺少分页和排序标准化
- ⚠️ 缺少事务边界检查
- ⚠️ 缺少查询缓存和性能监控

#### 建议补充：

##### 2.1 查询构建器增强
```python
# 应该支持
from aurimyth.foundation_kit.core.repository import BaseRepository

repo = UserRepository(session)

# 操作符支持
users = await repo.list(age__gt=18, name__like="张%", status__in=[1, 2, 3])

# 链式查询
users = await repo.query().filter(age__gt=18).order_by("-created_at").limit(10).all()
```

##### 2.2 批量操作优化
```python
# 应该提供
await repo.batch_create([...])  # 使用 bulk_insert_mappings
await repo.batch_update([...])  # 批量更新
await repo.bulk_upsert([...])   # 批量插入或更新
```

##### 2.3 分页和排序标准化
```python
# 应该提供
from aurimyth.foundation_kit.core.repository import PaginationParams, SortParams

result = await repo.paginate(
    PaginationParams(page=1, page_size=20),
    SortParams([("created_at", "desc"), ("id", "asc")])
)
# 返回 PaginationResult[T] 包含 items, total, page, page_size 等
```

##### 2.4 事务边界检查
```python
# 应该提供
from aurimyth.foundation_kit.core.repository import requires_transaction

@requires_transaction
async def update_user(repo, user, data):
    # 如果不在事务中，抛出 TransactionRequiredError
    await repo.update(user, data)
```

##### 2.5 查询缓存
```python
# 应该提供
from aurimyth.foundation_kit.core.repository import cache_query

@cache_query(ttl=300, key_prefix="user")
async def get_user_by_id(self, id: int):
    return await self.get(id)
```

##### 2.6 QueryInterceptor 接口
```python
# 应该提供
from aurimyth.foundation_kit.core.repository import QueryInterceptor

class AuditInterceptor(QueryInterceptor):
    async def before_query(self, query, **kwargs):
        # 自动添加审计条件
        pass
    
    async def after_query(self, result, **kwargs):
        # 记录查询日志
        pass
```

##### 2.7 类型安全增强
```python
# 应该提供
from typing import TypedDict

class UserFilter(TypedDict, total=False):
    name: str
    age: int
    status: int

# IDE 自动补全和类型检查
users = await repo.list(**UserFilter(name="张三", age=18))
```

**优先级**：🔴 **高**（提升开发体验和代码质量）

---

### 4. **Service 模式增强** ⭐⭐⭐⭐

#### 当前问题：
- ⚠️ Repository 需要手动创建
- ⚠️ 缺少服务组合和编排能力
- ⚠️ 缺少业务事件发布
- ⚠️ 缺少验证、缓存、监控装饰器

#### 建议补充：

##### 3.1 Repository 自动注入
```python
# 应该提供
from aurimyth.foundation_kit.core.service import BaseService, inject_repository

class UserService(BaseService):
    # 自动注入，支持多个 Repository
    user_repo: UserRepository = inject_repository()
    profile_repo: ProfileRepository = inject_repository()
```

##### 3.2 事务管理增强
```python
# 应该提供
from aurimyth.foundation_kit.core.service import transactional, readonly

@transactional(propagation=Propagation.REQUIRES_NEW)
async def create_user(self, data):
    # 支持事务传播级别
    pass

@readonly
async def get_user(self, id: int):
    # 只读事务优化
    pass
```

##### 3.3 业务事件发布
```python
# 应该提供
from aurimyth.foundation_kit.core.service import publish_event

@publish_event("user.created", after_commit=True)
@transactional
async def create_user(self, data):
    user = await self.user_repo.create(data)
    return user  # 事务提交后自动发布事件
```

##### 3.4 验证装饰器
```python
# 应该提供
from aurimyth.foundation_kit.core.service import validate
from pydantic import BaseModel

class CreateUserRequest(BaseModel):
    name: str
    email: str

@validate
async def create_user(self, data: CreateUserRequest):
    # 自动验证参数
    pass
```

##### 3.5 服务层缓存
```python
# 应该提供
from aurimyth.foundation_kit.core.service import cache_result

@cache_result(ttl=300, key=lambda self, id: f"user:{id}")
async def get_user(self, id: int):
    return await self.user_repo.get(id)
```

##### 3.6 性能监控装饰器
```python
# 应该提供
from aurimyth.foundation_kit.core.service import monitor

@monitor(metrics=True, slow_threshold=1.0)
async def create_user(self, data):
    # 自动记录执行时间和调用次数
    pass
```

**优先级**：🟡 **中**（提升开发体验，非必需）

---

## 📊 优先级总结

### 🔴 极高优先级（立即实施）

1. **可观测性增强** - 生产环境监控必需

### 🟡 高优先级（近期实施）

2. **测试框架增强** - 提高开发效率
3. **配置管理增强** - 多环境部署必需
4. **时区处理增强** - 完善时区转换功能
5. **ORM 可扩展性** - 提升框架灵活性和可扩展性
6. **Core 层优化（模型、Repository）** - 提升代码质量
7. **安全合规（数据脱敏）** - 应用层工具

### 🟢 中优先级（按需实施）

8. **Core 层优化（Service）** - 提升开发体验

---

## 🚀 实施路线图

### 第一阶段：安全核心（1-3个月）
1. ✅ 可观测性增强（健康检查、指标、追踪）

### 第二阶段：开发效率（4-6个月）
3. ✅ 测试框架增强
4. ✅ 配置管理增强
5. ✅ 时区处理增强（完善时区转换功能）
6. ✅ ORM 可扩展性（抽象层、多 ORM 支持）
7. ✅ Core 层优化（模型、Repository）

### 第三阶段：体验优化（7-9个月）
8. ✅ Core 层优化（Service）

---

## 💡 结论

### **真实差距分析**：

1. **可观测性增强** - 🔴 极高优先级
   - Spring Boot、NestJS 原生支持
   - Kit 只有基础支持
   - 生产环境监控必需

2. **安全合规** - 🟡 中优先级
   - 限流：由网关层提供（架构设计）
   - API Key：可由网关层或用户服务提供
   - 数据脱敏：应用层工具（需要补充）

3. **测试框架增强** - 🟡 高优先级
   - 所有框架都有完整支持
   - Kit 基础支持，需增强

5. **数据库迁移工具** - ✅ 已完整实现
   - Django、Laravel、Rails 原生支持
   - Kit 有基础支持，需增强便利性

### **Kit 的优势**：

- ✅ **异步支持**：原生异步，性能优于 Django、Laravel、Rails
- ✅ **类型提示**：完整的类型提示，优于 Django、Laravel、Rails
- ✅ **API 文档**：自动生成 OpenAPI 文档，优于所有框架
- ✅ **组件化架构**：灵活的组件系统，优于 Flask、FastAPI
- ✅ **Repository 模式**：原生支持，优于 Django、Laravel

### **总结**：

Kit 与顶级框架的真实差距主要集中在**安全、可观测性、测试**三个方面。这些功能都是企业级应用的核心需求，建议优先实施。Core 层的优化可以逐步进行，提升框架的健壮性和易用性。
