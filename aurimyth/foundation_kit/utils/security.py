"""安全工具类 - 密码、加密、签名。

提供完整的安全功能：
- 密码哈希和验证
- 加密/解密
- 数字签名
- 密码强度验证
- 安全随机数生成
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator

from aurimyth.foundation_kit.utils.logging import logger


class PasswordPolicy(BaseModel):
    """密码策略配置（Pydantic）。
    
    Attributes:
        min_length: 最小长度
        require_uppercase: 需要大写字母
        require_lowercase: 需要小写字母
        require_digit: 需要数字
        require_special: 需要特殊字符
    """
    
    min_length: int = Field(8, ge=4, le=128, description="最小长度")
    require_uppercase: bool = Field(True, description="需要大写字母")
    require_lowercase: bool = Field(True, description="需要小写字母")
    require_digit: bool = Field(True, description="需要数字")
    require_special: bool = Field(False, description="需要特殊字符")
    
    @validator("min_length")
    def validate_min_length(cls, v: int) -> int:
        """验证最小长度。"""
        if v < 4:
            raise ValueError("密码最小长度不能小于4")
        return v


class PasswordStrength:
    """密码强度评估结果。"""
    
    def __init__(
        self,
        score: int,
        is_valid: bool,
        feedback: list[str],
    ):
        self.score = score  # 0-4: 很弱、弱、中等、强、很强
        self.is_valid = is_valid
        self.feedback = feedback
    
    def __repr__(self) -> str:
        levels = ["很弱", "弱", "中等", "强", "很强"]
        level = levels[min(self.score, 4)]
        return f"<PasswordStrength level={level} score={self.score} valid={self.is_valid}>"


class SecurityManager:
    """安全管理器 - 单例模式。
    
    提供各种安全功能：
    - 密码哈希和验证
    - 对称加密（Fernet）
    - 消息签名（HMAC）
    - 密码强度验证
    - 安全随机数生成
    """
    
    _instance: Optional[SecurityManager] = None
    
    def __init__(self) -> None:
        """私有构造函数。"""
        if SecurityManager._instance is not None:
            raise RuntimeError("SecurityManager 是单例类，请使用 get_instance() 获取实例")
        
        self._default_policy = PasswordPolicy()
        self._fernet_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
    
    @classmethod
    def get_instance(cls) -> SecurityManager:
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ==================== 密码哈希 ====================
    
    def hash_password(self, password: str, rounds: int = 12) -> str:
        """哈希密码（bcrypt）。
        
        Args:
            password: 明文密码
            rounds: bcrypt轮数（默认12，范围4-31）
            
        Returns:
            str: 哈希后的密码
        """
        if not password:
            raise ValueError("密码不能为空")
        
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码。
        
        Args:
            password: 明文密码
            hashed: 哈希密码
            
        Returns:
            bool: 是否匹配
        """
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except (ValueError, TypeError) as exc:
            logger.warning(f"密码验证失败: {exc}")
            return False
    
    # ==================== 密码强度验证 ====================
    
    def validate_password(
        self,
        password: str,
        policy: Optional[PasswordPolicy] = None,
    ) -> PasswordStrength:
        """验证密码强度。
        
        Args:
            password: 密码
            policy: 密码策略
            
        Returns:
            PasswordStrength: 密码强度评估结果
        """
        policy = policy or self._default_policy
        feedback = []
        score = 0
        
        # 检查长度
        if len(password) < policy.min_length:
            feedback.append(f"密码长度至少{policy.min_length}个字符")
        else:
            score += 1
        
        # 检查大写字母
        has_uppercase = any(c.isupper() for c in password)
        if policy.require_uppercase and not has_uppercase:
            feedback.append("需要包含大写字母")
        elif has_uppercase:
            score += 1
        
        # 检查小写字母
        has_lowercase = any(c.islower() for c in password)
        if policy.require_lowercase and not has_lowercase:
            feedback.append("需要包含小写字母")
        elif has_lowercase:
            score += 1
        
        # 检查数字
        has_digit = any(c.isdigit() for c in password)
        if policy.require_digit and not has_digit:
            feedback.append("需要包含数字")
        elif has_digit:
            score += 1
        
        # 检查特殊字符
        special_chars = set(string.punctuation)
        has_special = any(c in special_chars for c in password)
        if policy.require_special and not has_special:
            feedback.append("需要包含特殊字符")
        elif has_special:
            score += 1
        
        # 额外分数：长度
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        is_valid = len(feedback) == 0
        
        if is_valid:
            feedback.append("密码强度良好")
        
        return PasswordStrength(
            score=min(score, 4),
            is_valid=is_valid,
            feedback=feedback,
        )
    
    # ==================== 对称加密 ====================
    
    def initialize_encryption(self, key: Optional[bytes] = None) -> None:
        """初始化加密器。
        
        Args:
            key: Fernet密钥（32字节），不提供则自动生成
        """
        if key is None:
            key = Fernet.generate_key()
            logger.warning("使用自动生成的加密密钥，请妥善保存")
        
        self._fernet_key = key
        self._fernet = Fernet(key)
        logger.info("加密器已初始化")
    
    @property
    def fernet(self) -> Fernet:
        """获取Fernet加密器。"""
        if self._fernet is None:
            raise RuntimeError("加密器未初始化，请先调用 initialize_encryption()")
        return self._fernet
    
    def encrypt(self, data: str) -> str:
        """加密字符串。
        
        Args:
            data: 明文
            
        Returns:
            str: 密文（Base64）
        """
        encrypted = self.fernet.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串。
        
        Args:
            encrypted_data: 密文（Base64）
            
        Returns:
            str: 明文
        """
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    # ==================== 消息签名 ====================
    
    def sign_message(self, message: str, secret: str) -> str:
        """使用HMAC签名消息。
        
        Args:
            message: 消息
            secret: 密钥
            
        Returns:
            str: 签名（十六进制）
        """
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature
    
    def verify_signature(self, message: str, signature: str, secret: str) -> bool:
        """验证消息签名。
        
        Args:
            message: 消息
            signature: 签名
            secret: 密钥
            
        Returns:
            bool: 是否有效
        """
        expected_signature = self.sign_message(message, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    # ==================== 哈希 ====================
    
    def hash_sha256(self, data: str) -> str:
        """SHA256哈希。
        
        Args:
            data: 数据
            
        Returns:
            str: 哈希值（十六进制）
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    def hash_md5(self, data: str) -> str:
        """MD5哈希（不推荐用于安全场景）。
        
        Args:
            data: 数据
            
        Returns:
            str: 哈希值（十六进制）
        """
        return hashlib.md5(data.encode()).hexdigest()
    
    # ==================== 随机生成 ====================
    
    def generate_token(self, length: int = 32) -> str:
        """生成安全随机token。
        
        Args:
            length: 字节长度
            
        Returns:
            str: URL安全的token
        """
        return secrets.token_urlsafe(length)
    
    def generate_hex_token(self, length: int = 32) -> str:
        """生成十六进制随机token。
        
        Args:
            length: 字节长度
            
        Returns:
            str: 十六进制token
        """
        return secrets.token_hex(length)
    
    def generate_password(
        self,
        length: int = 16,
        *,
        use_uppercase: bool = True,
        use_lowercase: bool = True,
        use_digits: bool = True,
        use_special: bool = True,
    ) -> str:
        """生成安全随机密码。
        
        Args:
            length: 密码长度
            use_uppercase: 使用大写字母
            use_lowercase: 使用小写字母
            use_digits: 使用数字
            use_special: 使用特殊字符
            
        Returns:
            str: 随机密码
        """
        chars = ""
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_lowercase:
            chars += string.ascii_lowercase
        if use_digits:
            chars += string.digits
        if use_special:
            chars += string.punctuation
        
        if not chars:
            raise ValueError("至少选择一种字符类型")
        
        # 确保密码包含所有选择的字符类型
        password = []
        if use_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if use_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if use_digits:
            password.append(secrets.choice(string.digits))
        if use_special:
            password.append(secrets.choice(string.punctuation))
        
        # 填充剩余长度
        password.extend(secrets.choice(chars) for _ in range(length - len(password)))
        
        # 打乱顺序
        secrets.SystemRandom().shuffle(password)
        
        return "".join(password)
    
    def __repr__(self) -> str:
        """字符串表示。"""
        encryption_status = "enabled" if self._fernet is not None else "disabled"
        return f"<SecurityManager encryption={encryption_status}>"


# 全局实例
_security_manager = SecurityManager.get_instance()


# 便捷函数
def hash_secret(secret: str) -> str:
    """哈希密码。"""
    return _security_manager.hash_password(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    """验证密码。"""
    return _security_manager.verify_password(secret, hashed)


# 新增便捷函数
def validate_password_strength(
    password: str,
    policy: Optional[PasswordPolicy] = None,
) -> PasswordStrength:
    """验证密码强度。"""
    return _security_manager.validate_password(password, policy)


def generate_secure_token(length: int = 32) -> str:
    """生成安全token。"""
    return _security_manager.generate_token(length)


def generate_random_password(length: int = 16) -> str:
    """生成随机密码。"""
    return _security_manager.generate_password(length)


__all__ = [
    "SecurityManager",
    "PasswordPolicy",
    "PasswordStrength",
    "hash_secret",
    "verify_secret",
    "validate_password_strength",
    "generate_secure_token",
    "generate_random_password",
]
