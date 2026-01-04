"""第三方接口适配器配置模型。

提供统一的配置结构，支持：
- 多模式切换（real/sandbox/mock/disabled）
- 按方法级别的模式覆盖
- 通用连接参数（URL、认证、超时等）
- 挡板（Mock）策略配置

模式说明:
- real: 调用真实第三方接口（生产环境）
- sandbox: 调用第三方提供的沙箱环境
- mock: 使用本地挡板实现，不发出真实请求（测试/开发环境）
- disabled: 禁用该接口，调用时抛出 AdapterDisabledError
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 适配器模式类型
# - real: 真实调用第三方接口
# - sandbox: 调用第三方沙箱环境
# - mock: 使用本地挡板实现
# - disabled: 禁用，调用时抛出异常
AdapterMode = Literal["real", "sandbox", "mock", "disabled"]

# 挡板（Mock）策略类型
# - success: 返回成功响应
# - failure: 返回失败响应
# - echo: 回显请求参数
# - noop: 空操作，返回空结果
# - custom: 自定义，使用 @method.mock 定义的处理函数
MockStrategy = Literal["success", "failure", "echo", "noop", "custom"]


class AdapterSettings(BaseModel):
    """第三方接口适配器配置。
    
    通用的第三方服务配置模型，支持多模式切换和按方法覆盖。
    
    配置项分类:
    1. 基础配置: enabled, mode
    2. 连接配置: base_url, sandbox_url, api_key, api_secret, timeout, retry_times
    3. 模式覆盖: method_modes - 按方法名覆盖全局模式
    4. 挡板配置: mock_strategy, mock_default_response, mock_delay, mock_method_responses
    
    环境变量配置示例:
        # 基础配置
        THIRD_PARTY_PAYMENT_ENABLED=true
        THIRD_PARTY_PAYMENT_MODE=mock          # 测试环境用挡板
        
        # 连接配置
        THIRD_PARTY_PAYMENT_BASE_URL=https://api.payment.com
        THIRD_PARTY_PAYMENT_SANDBOX_URL=https://sandbox.payment.com
        THIRD_PARTY_PAYMENT_API_KEY=sk_live_xxx
        THIRD_PARTY_PAYMENT_TIMEOUT=30
        
        # 方法级模式覆盖（JSON 格式）
        # query 走真实接口，refund 禁用
        THIRD_PARTY_PAYMENT_METHOD_MODES={"query": "real", "refund": "disabled"}
        
        # 挡板配置
        THIRD_PARTY_PAYMENT_MOCK_DELAY=0.1     # 模拟网络延迟 100ms
    """
    
    # ========== 基础配置 ==========
    enabled: bool = Field(
        default=True,
        description="是否启用此集成",
    )
    mode: AdapterMode = Field(
        default="real",
        description="当前模式：real(生产)/sandbox(沙箱)/mock(挡板)/disabled(禁用)",
    )
    
    # ========== 连接配置 ==========
    base_url: str | None = Field(
        default=None,
        description="服务基础 URL（生产环境）",
    )
    sandbox_url: str | None = Field(
        default=None,
        description="沙箱环境 URL（sandbox 模式时优先使用）",
    )
    api_key: str | None = Field(
        default=None,
        description="API 密钥（如 Authorization header）",
    )
    api_secret: str | None = Field(
        default=None,
        description="API 密钥（用于签名等）",
    )
    timeout: int = Field(
        default=30,
        description="请求超时（秒）",
    )
    retry_times: int = Field(
        default=3,
        description="重试次数",
    )
    
    # ========== 模式覆盖 ==========
    method_modes: dict[str, AdapterMode] = Field(
        default_factory=dict,
        description="按方法覆盖模式，如 {'refund': 'disabled', 'query': 'real'}",
    )
    
    # ========== Mock 配置 ==========
    mock_strategy: MockStrategy = Field(
        default="success",
        description="默认 mock 策略：success(成功)/failure(失败)/echo(回显)/noop(空操作)/custom(自定义)",
    )
    mock_default_response: dict[str, Any] | None = Field(
        default=None,
        description="默认 mock 响应（当没有自定义 mock handler 时使用）",
    )
    mock_delay: float = Field(
        default=0.0,
        description="mock 模拟延迟（秒），用于模拟网络延迟",
    )
    mock_method_responses: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="按方法的 mock 响应，如 {'create': {'success': True, 'id': 'mock-123'}}",
    )
    
    # ========== 扩展配置 ==========
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="额外配置（供子类或特定第三方使用）",
    )
    
    def get_effective_url(self) -> str | None:
        """获取当前模式下的有效 URL。
        
        sandbox 模式优先使用 sandbox_url，否则使用 base_url。
        """
        if self.mode == "sandbox" and self.sandbox_url:
            return self.sandbox_url
        return self.base_url
    
    def get_method_mode(self, method_name: str) -> AdapterMode:
        """获取指定方法的有效模式。
        
        优先使用 method_modes 中的配置，否则使用全局 mode。
        
        Args:
            method_name: 方法名称
            
        Returns:
            AdapterMode: 有效模式
        """
        return self.method_modes.get(method_name, self.mode)
    
    def is_method_enabled(self, method_name: str) -> bool:
        """检查指定方法是否启用。
        
        Args:
            method_name: 方法名称
            
        Returns:
            bool: 是否启用
        """
        if not self.enabled:
            return False
        return self.get_method_mode(method_name) != "disabled"
    
    def get_mock_response(self, method_name: str) -> dict[str, Any] | None:
        """获取指定方法的 mock 响应。
        
        优先使用 mock_method_responses，否则使用 mock_default_response。
        
        Args:
            method_name: 方法名称
            
        Returns:
            dict | None: mock 响应
        """
        return self.mock_method_responses.get(method_name, self.mock_default_response)


class ThirdPartySettings(BaseSettings):
    """第三方服务配置聚合。
    
    将所有第三方服务的配置聚合到一个类中，便于统一管理。
    项目可以继承此类添加更多第三方服务。
    
    环境变量前缀: THIRD_PARTY_
    
    使用示例:
        class MyThirdPartySettings(ThirdPartySettings):
            wechat: AdapterSettings = Field(default_factory=AdapterSettings)
            alipay: AdapterSettings = Field(default_factory=AdapterSettings)
        
        # 环境变量
        THIRD_PARTY_WECHAT_MODE=sandbox
        THIRD_PARTY_ALIPAY_MODE=mock
    """
    
    # 示例：常见第三方服务（项目可以继承并添加）
    # payment: AdapterSettings = Field(default_factory=AdapterSettings)
    # sms: AdapterSettings = Field(default_factory=AdapterSettings)
    # oss: AdapterSettings = Field(default_factory=AdapterSettings)
    # email: AdapterSettings = Field(default_factory=AdapterSettings)
    
    model_config = SettingsConfigDict(
        env_prefix="THIRD_PARTY_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )
    
    def set_all_mode(self, mode: AdapterMode) -> None:
        """将所有第三方服务设置为指定模式。
        
        便捷方法，用于测试环境一键切换所有服务到 mock 模式。
        
        Args:
            mode: 目标模式
        """
        for field_name in self.model_fields:
            field_value = getattr(self, field_name, None)
            if isinstance(field_value, AdapterSettings):
                field_value.mode = mode
    
    def disable_all(self) -> None:
        """禁用所有第三方服务。"""
        self.set_all_mode("disabled")
    
    def mock_all(self) -> None:
        """将所有第三方服务设置为 mock 模式。"""
        self.set_all_mode("mock")


__all__ = [
    "AdapterMode",
    "AdapterSettings",
    "MockStrategy",
    "ThirdPartySettings",
]
