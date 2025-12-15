# 19. 国际化完整指南

请参考 [00-quick-start.md](./00-quick-start.md) 第 19 章的基础用法。

## 翻译加载

### 基础翻译

```python
from aury.boot.common.i18n.translator import translate, load_translations

# 加载翻译
load_translations({
    "zh_CN": {
        "hello": "你好",
        "goodbye": "再见",
        "error.not_found": "资源 {name} 未找到",
    },
    "en_US": {
        "hello": "Hello",
        "goodbye": "Goodbye",
        "error.not_found": "Resource {name} not found",
    },
    "ja_JP": {
        "hello": "こんにちは",
        "goodbye": "さようなら",
        "error.not_found": "リソース {name} が見つかりません",
    }
})
```

### 从文件加载

```python
import json
import yaml

# 从 JSON 文件
def load_translations_from_json():
    with open("translations/zh_CN.json", "r", encoding="utf-8") as f:
        zh_translations = json.load(f)
    
    with open("translations/en_US.json", "r", encoding="utf-8") as f:
        en_translations = json.load(f)
    
    load_translations({
        "zh_CN": zh_translations,
        "en_US": en_translations,
    })

# 从 YAML 文件
def load_translations_from_yaml():
    with open("translations/zh_CN.yaml", "r", encoding="utf-8") as f:
        zh_translations = yaml.safe_load(f)
    
    load_translations({"zh_CN": zh_translations})
```

## 翻译使用

### 简单翻译

```python
# 中文
msg = translate("hello", locale="zh_CN")
# 输出: "你好"

# 英文
msg = translate("hello", locale="en_US")
# 输出: "Hello"
```

### 带参数的翻译

```python
# 中文 - 资源 User 未找到
msg = translate("error.not_found", locale="zh_CN", name="User")
# 输出: "资源 User 未找到"

# 英文 - Resource User not found
msg = translate("error.not_found", locale="en_US", name="User")
# 输出: "Resource User not found"
```

### 默认语言

```python
# 设置默认语言为中文
msg = translate("hello")  # 使用默认语言
```

## API 集成

### 根据请求语言返回

```python
from fastapi import APIRouter, Header
from aury.boot.application.interfaces.egress import BaseResponse

router = APIRouter()

@router.get("/data")
async def get_data(accept_language: str = Header(default="zh-CN")):
    """根据请求的语言返回数据"""
    
    # 转换语言代码 (en-US -> en_US)
    locale = accept_language.replace("-", "_")
    
    message = translate("hello", locale=locale)
    
    return BaseResponse(
        code=200,
        message=message,
        data={"greeting": message}
    )

@router.get("/users/{user_id}")
async def get_user(user_id: str, accept_language: str = Header(default="zh-CN")):
    """获取用户信息，返回本地化错误"""
    
    locale = accept_language.replace("-", "_")
    
    user = await db.get_user(user_id)
    if not user:
        error_msg = translate("error.not_found", locale=locale, name="User")
        return BaseResponse(code=404, message=error_msg)
    
    return BaseResponse(code=200, message="Success", data=user)
```

### 错误消息国际化

```python
from aury.boot.application.errors import NotFoundError

def get_locale_from_request(request):
    """从请求中提取语言"""
    language = request.headers.get("accept-language", "zh-CN")
    return language.replace("-", "_")

@router.get("/items/{item_id}")
async def get_item(item_id: str, request):
    locale = get_locale_from_request(request)
    
    item = await db.get_item(item_id)
    if not item:
        # 使用本地化错误消息
        error_msg = translate("error.not_found", locale=locale, name="Item")
        raise NotFoundError(error_msg)
    
    return BaseResponse(code=200, message="Success", data=item)
```

## 常见场景

### 表单验证消息

```python
from pydantic import BaseModel, field_validator

class UserRegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    
    @field_validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            # 返回本地化错误信息
            raise ValueError("username_too_short")
        return v

@router.post("/auth/register")
async def register(request: UserRegisterRequest, accept_language: str = Header()):
    locale = accept_language.replace("-", "_")
    
    try:
        # 验证用户
        user = await user_service.register(request)
        success_msg = translate("auth.register_success", locale=locale)
        return BaseResponse(code=200, message=success_msg, data={"user_id": user.id})
    
    except ValueError as e:
        error_msg = translate(f"error.{str(e)}", locale=locale)
        return BaseResponse(code=400, message=error_msg)
```

### 邮件模板国际化

```python
class EmailService:
    def get_template(self, template_name: str, locale: str):
        """获取本地化的邮件模板"""
        
        templates = {
            "zh_CN": {
                "welcome": "欢迎 {name}！",
                "reset_password": "点击链接重置密码: {link}",
            },
            "en_US": {
                "welcome": "Welcome {name}!",
                "reset_password": "Click the link to reset password: {link}",
            }
        }
        
        return templates.get(locale, templates["en_US"]).get(template_name, "")
    
    async def send_welcome_email(self, user: User, locale: str):
        """发送欢迎邮件"""
        
        subject = translate("email.welcome_subject", locale=locale)
        template = self.get_template("welcome", locale)
        content = template.format(name=user.name)
        
        await self.send(
            to=user.email,
            subject=subject,
            content=content
        )
```

### 日期和时间本地化

```python
from datetime import datetime

def format_datetime(dt: datetime, locale: str):
    """本地化日期时间格式"""
    
    formats = {
        "zh_CN": "%Y年%m月%d日 %H:%M:%S",
        "en_US": "%m/%d/%Y %I:%M:%S %p",
        "ja_JP": "%Y年%m月%d日 %H:%M:%S",
    }
    
    fmt = formats.get(locale, formats["en_US"])
    return dt.strftime(fmt)

# 使用
dt = datetime.now()
print(format_datetime(dt, "zh_CN"))  # 2024年01月15日 14:30:45
print(format_datetime(dt, "en_US"))  # 01/15/2024 02:30:45 PM
```

### 数字和货币本地化

```python
from decimal import Decimal

def format_currency(amount: Decimal, locale: str, currency: str = "USD"):
    """本地化货币格式"""
    
    if locale == "zh_CN":
        if currency == "CNY":
            return f"¥{amount:.2f}"
        return f"${amount:.2f}"
    elif locale == "en_US":
        return f"{currency} {amount:.2f}"
    elif locale == "ja_JP":
        if currency == "JPY":
            return f"¥{int(amount)}"
        return f"{currency} {amount:.2f}"
    
    return f"{currency} {amount:.2f}"

# 使用
price = Decimal("100.50")
print(format_currency(price, "zh_CN", "CNY"))  # ¥100.50
print(format_currency(price, "en_US", "USD"))  # USD 100.50
print(format_currency(price, "ja_JP", "JPY"))  # ¥101
```

## 文件组织

### 推荐的目录结构

```
app/
├── i18n/
│   ├── translations/
│   │   ├── zh_CN.json
│   │   ├── en_US.json
│   │   └── ja_JP.json
│   └── loader.py
└── main.py
```

### translations/zh_CN.json

```json
{
  "hello": "你好",
  "goodbye": "再见",
  "auth": {
    "login_success": "登录成功",
    "logout_success": "退出成功"
  },
  "error": {
    "not_found": "资源 {name} 未找到",
    "unauthorized": "未授权",
    "forbidden": "禁止访问"
  },
  "email": {
    "welcome_subject": "欢迎加入",
    "reset_password_subject": "重置密码"
  }
}
```

## 性能优化

### 缓存翻译

```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def get_translation(key: str, locale: str):
    """缓存翻译结果"""
    return translate(key, locale=locale)
```

### 预加载翻译

```python
# 在应用启动时加载所有翻译
@app.on_event("startup")
async def load_i18n():
    """预加载国际化资源"""
    
    translations = {}
    
    for locale in ["zh_CN", "en_US", "ja_JP"]:
        with open(f"translations/{locale}.json", "r", encoding="utf-8") as f:
            translations[locale] = json.load(f)
    
    load_translations(translations)
    logger.info("国际化资源已加载")
```

---

**总结**：国际化支持多语言用户，通过翻译和格式化实现更好的用户体验。设计好的国际化方案可以让应用轻松支持全球用户。
