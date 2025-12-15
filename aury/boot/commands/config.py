"""项目配置读取工具。

读取和写入 pyproject.toml 中的 [tool.aury] 配置。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectConfig:
    """Aury 项目配置。"""

    package: str | None = None  # 顶层包名，None 表示无顶层包
    app: str | None = None      # 应用入口，形如 "main:app"

    @property
    def has_package(self) -> bool:
        """是否有顶层包。"""
        return self.package is not None and self.package != ""

    def get_import_prefix(self) -> str:
        """获取 import 前缀。

        有包名返回 "mypackage."，无包名返回 ""。
        """
        return f"{self.package}." if self.has_package else ""

    def get_package_dir(self, base_path: Path) -> Path:
        """获取包目录路径。

        有包名返回 base_path/mypackage，无包名返回 base_path。
        """
        return base_path / self.package if self.has_package else base_path


def get_project_config(base_path: Path | None = None) -> ProjectConfig:
    """读取项目配置。

    从 pyproject.toml 的 [tool.aury] 读取配置。

    Args:
        base_path: 项目根目录，默认为当前目录

    Returns:
        ProjectConfig 实例
    """
    if base_path is None:
        base_path = Path.cwd()

    pyproject_path = base_path / "pyproject.toml"

    if not pyproject_path.exists():
        return ProjectConfig()

    content = pyproject_path.read_text(encoding="utf-8")

    # 简单解析 [tool.aury] 部分
    package = _parse_toml_value(content, "tool.aury", "package")
    app = _parse_toml_value(content, "tool.aury", "app")

    return ProjectConfig(package=package, app=app)


def save_project_config(config: ProjectConfig, base_path: Path | None = None) -> bool:
    """保存项目配置到 pyproject.toml。

    Args:
        config: 项目配置
        base_path: 项目根目录

    Returns:
        是否保存成功
    """
    if base_path is None:
        base_path = Path.cwd()

    pyproject_path = base_path / "pyproject.toml"

    if not pyproject_path.exists():
        return False

    content = pyproject_path.read_text(encoding="utf-8")

    # 检查是否已有 [tool.aury] 部分
    if "[tool.aury]" in content:
        # 更新现有配置
        lines = content.split("\n")
        new_lines = []
        in_aury_section = False

        for line in lines:
            if line.strip() == "[tool.aury]":
                in_aury_section = True
                new_lines.append(line)
                # 添加（或更新）配置项
                if config.has_package:
                    new_lines.append(f'package = "{config.package}"')
                if config.app:
                    new_lines.append(f'app = "{config.app}"')
                continue

            if in_aury_section:
                # 跳过旧的 package/app 配置
                if line.strip().startswith("package") or line.strip().startswith("app"):
                    continue
                # 遇到新的 section 结束
                if line.strip().startswith("["):
                    in_aury_section = False

            new_lines.append(line)

        content = "\n".join(new_lines)
    else:
        # 添加新的 [tool.aury] 部分
        aury_section = "\n[tool.aury]\n"
        if config.has_package:
            aury_section += f'package = "{config.package}"\n'
        if config.app:
            aury_section += f'app = "{config.app}"\n'

        content += aury_section

    pyproject_path.write_text(content, encoding="utf-8")
    return True


def _parse_toml_value(content: str, section: str, key: str) -> str | None:
    """简单解析 TOML 值。

    注意：这是一个简单实现，不处理复杂情况。

    Args:
        content: TOML 文件内容
        section: 节名（如 "tool.aury"）
        key: 键名

    Returns:
        值字符串，找不到返回 None
    """
    import re

    # 构建 section 匹配
    section_pattern = r"\[" + re.escape(section) + r"\]"

    # 查找 section
    section_match = re.search(section_pattern, content)
    if not section_match:
        return None

    # 从 section 开始查找 key
    section_start = section_match.end()

    # 查找下一个 section（或文件结尾）
    next_section = re.search(r"\n\[", content[section_start:])
    if next_section:
        section_content = content[section_start : section_start + next_section.start()]
    else:
        section_content = content[section_start:]

    # 查找 key = value
    key_pattern = rf"^\s*{re.escape(key)}\s*=\s*[\"']?([^\"'\n]+)[\"']?\s*$"
    key_match = re.search(key_pattern, section_content, re.MULTILINE)

    if key_match:
        return key_match.group(1).strip().strip("\"'")

    return None


__all__ = [
    "ProjectConfig",
    "get_project_config",
    "save_project_config",
]
