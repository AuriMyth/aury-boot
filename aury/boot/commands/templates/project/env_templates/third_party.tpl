
# =============================================================================
# 第三方接口适配器配置 (THIRD_PARTY__)
# =============================================================================
# 用于配置支付、短信、微信等第三方接口的模式切换和挡板设置
# 格式: THIRD_PARTY__{{ADAPTER_NAME}}__{{FIELD}}
#
# 模式说明:
# - real: 真实调用第三方接口（生产环境）
# - sandbox: 调用第三方沙箱环境（如果有）
# - mock: 使用本地挡板实现，不发出真实请求（测试/开发环境）
# - disabled: 禁用该接口，调用时抛出 AdapterDisabledError
#
# ---------- 支付接口示例 (PAYMENT) ----------
# THIRD_PARTY__PAYMENT__ENABLED=true
# THIRD_PARTY__PAYMENT__MODE=mock
# THIRD_PARTY__PAYMENT__BASE_URL=https://api.payment.com/v1
# THIRD_PARTY__PAYMENT__SANDBOX_URL=https://sandbox.payment.com/v1
# THIRD_PARTY__PAYMENT__API_KEY=sk_live_xxx
# THIRD_PARTY__PAYMENT__API_SECRET=
# THIRD_PARTY__PAYMENT__TIMEOUT=30
# THIRD_PARTY__PAYMENT__RETRY_TIMES=3
# THIRD_PARTY__PAYMENT__METHOD_MODES={{"query": "real", "refund": "disabled"}}
# THIRD_PARTY__PAYMENT__MOCK_STRATEGY=success
# THIRD_PARTY__PAYMENT__MOCK_DELAY=0.1
# THIRD_PARTY__PAYMENT__MOCK_DEFAULT_RESPONSE={{"success": true, "mock": true}}
#
# ---------- 短信接口示例 (SMS) ----------
# THIRD_PARTY__SMS__ENABLED=true
# THIRD_PARTY__SMS__MODE=mock
# THIRD_PARTY__SMS__BASE_URL=https://sms.aliyuncs.com
# THIRD_PARTY__SMS__API_KEY=LTAI5xxx
# THIRD_PARTY__SMS__API_SECRET=xxx
# THIRD_PARTY__SMS__TIMEOUT=10
# THIRD_PARTY__SMS__MOCK_STRATEGY=success
# THIRD_PARTY__SMS__MOCK_DEFAULT_RESPONSE={{"code": "OK", "message": "mock sent"}}
#
# ---------- 微信接口示例 (WECHAT) ----------
# THIRD_PARTY__WECHAT__ENABLED=true
# THIRD_PARTY__WECHAT__MODE=mock
# THIRD_PARTY__WECHAT__BASE_URL=https://api.weixin.qq.com
# THIRD_PARTY__WECHAT__TIMEOUT=15
# THIRD_PARTY__WECHAT__EXTRA={{"appid": "wx123", "secret": "xxx"}}
