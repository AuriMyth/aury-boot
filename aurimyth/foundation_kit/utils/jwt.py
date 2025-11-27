"""JWT Token模型定义。

提供Token相关的数据模型，供用户中心服务使用。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Literal

from pydantic import BaseModel, Field


class TokenType(str, Enum):
    """Token类型。"""
    
    ACCESS = "access"
    REFRESH = "refresh"
    SESSION = "session"
    VERIFICATION = "verification"
    RESET_PASSWORD = "reset_password"


class TokenPayload(BaseModel):
    """Token载荷（Pydantic）。
    
    所有Token的基础结构。
    """
    
    sub: str = Field(..., description="主题（通常是用户ID）")
    type: TokenType = Field(..., description="Token类型")
    exp: datetime = Field(..., description="过期时间")
    iat: datetime = Field(default_factory=datetime.utcnow, description="签发时间")
    jti: Optional[str] = Field(None, description="Token ID")
    
    class Config:
        use_enum_values = True


class AccessTokenPayload(TokenPayload):
    """访问Token载荷。"""
    
    type: Literal[TokenType.ACCESS] = TokenType.ACCESS
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    tenant_id: Optional[int] = Field(None, description="租户ID")
    application_id: Optional[int] = Field(None, description="应用ID")


class RefreshTokenPayload(TokenPayload):
    """刷新Token载荷。"""
    
    type: Literal[TokenType.REFRESH] = TokenType.REFRESH


class SessionTokenPayload(TokenPayload):
    """会话Token载荷。"""
    
    type: Literal[TokenType.SESSION] = TokenType.SESSION
    device_id: Optional[str] = Field(None, description="设备ID")
    device_type: Optional[str] = Field(None, description="设备类型")


class VerificationTokenPayload(TokenPayload):
    """验证Token载荷。"""
    
    type: Literal[TokenType.VERIFICATION] = TokenType.VERIFICATION
    purpose: str = Field(..., description="验证目的")


class ResetPasswordTokenPayload(TokenPayload):
    """重置密码Token载荷。"""
    
    type: Literal[TokenType.RESET_PASSWORD] = TokenType.RESET_PASSWORD


__all__ = [
    "TokenType",
    "TokenPayload",
    "AccessTokenPayload",
    "RefreshTokenPayload",
    "SessionTokenPayload",
    "VerificationTokenPayload",
    "ResetPasswordTokenPayload",
]
