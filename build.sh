#!/bin/bash

# AuriMyth Foundation Kit - 打包脚本（使用 uv）
#
# 使用方法:
#   ./build.sh
#
# 功能:
#   1. 检查 Git 状态和版本
#   2. 清理旧的构建文件
#   3. 构建包（wheel 和 source distribution）
#   4. 检查构建产物
#
# 版本管理:
#   版本号通过 Git 标签自动管理（hatch-vcs）
#   创建新版本: git tag v0.1.0 && git push --tags

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 打印函数
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 uv
check_uv() {
    if ! command -v uv &> /dev/null; then
        error "未找到 uv，请先安装:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    success "uv $(uv --version | head -1)"
}

# 从 pyproject.toml 读取版本文件路径
get_version_file() {
    local pyproject="pyproject.toml"
    local version_file
    
    if [ ! -f "$pyproject" ]; then
        return 1
    fi
    
    # 尝试使用 Python 解析 TOML（更可靠）
    if command -v python3 &> /dev/null; then
        version_file=$(python3 <<PYTHON_SCRIPT 2>/dev/null
import re
import sys

try:
    with open("$pyproject", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 查找 [tool.hatch.build.hooks.vcs] 部分的 version-file
    pattern = r'\[tool\.hatch\.build\.hooks\.vcs\].*?version-file\s*=\s*"([^"]+)"'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        print(match.group(1))
        sys.exit(0)
except Exception:
    pass

sys.exit(1)
PYTHON_SCRIPT
)
        if [ $? -eq 0 ] && [ -n "$version_file" ]; then
            echo "$version_file"
            return 0
        fi
    fi
    
    # 备用方案：使用 grep/sed（简单但可能不够健壮）
    if grep -q '\[tool\.hatch\.build\.hooks\.vcs\]' "$pyproject" 2>/dev/null; then
        version_file=$(sed -n '/\[tool\.hatch\.build\.hooks\.vcs\]/,/^\[/p' "$pyproject" | \
            grep 'version-file' | \
            sed -E 's/.*version-file\s*=\s*"([^"]+)".*/\1/' | \
            head -1)
        if [ -n "$version_file" ]; then
            echo "$version_file"
            return 0
        fi
    fi
    
    return 1
}

# 检查 Git 状态
check_git() {
    info "检查 Git 状态..."
    
    # 检查是否在 Git 仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "当前目录不是 Git 仓库"
        exit 1
    fi
    
    # 获取当前版本（从 git describe）
    if git describe --tags --always > /dev/null 2>&1; then
        VERSION=$(git describe --tags --always --dirty)
        info "当前版本: ${CYAN}${VERSION}${NC}"
    else
        warning "未找到 Git 标签，将使用 0.0.0.devN 格式版本"
        VERSION="0.0.0.dev$(git rev-list --count HEAD)"
        info "开发版本: ${CYAN}${VERSION}${NC}"
    fi
    
    # 检查是否有未提交的更改（只检查已追踪的文件，忽略未追踪文件）
    if [[ -n $(git status --porcelain | grep -v "^??") ]]; then
        warning "存在未提交的更改，版本号将带有 +dirty 后缀"
    fi
}

# 清理构建产物
clean() {
    info "清理旧的构建文件..."
    
    # 清理构建目录和临时文件
    rm -rf build/ dist/ *.egg-info aury/*.egg-info
    
    # 从 pyproject.toml 读取版本文件路径
    VERSION_FILE=$(get_version_file || echo "")
    
    if [ -n "$VERSION_FILE" ]; then
        info "检测到版本文件: ${CYAN}${VERSION_FILE}${NC}"
        
        # 如果版本文件被 Git 追踪，先从索引中移除
        if git ls-files --error-unmatch "$VERSION_FILE" > /dev/null 2>&1; then
            info "从 Git 索引中移除版本文件..."
            git rm --cached "$VERSION_FILE" > /dev/null 2>&1 || true
        fi
        
        # 删除本地版本文件（.gitignore 会忽略它）
        if [ -f "$VERSION_FILE" ]; then
            rm -f "$VERSION_FILE"
        fi
    else
        # 如果没有配置版本文件，尝试查找常见的版本文件
        info "未在 pyproject.toml 中找到版本文件配置，跳过版本文件清理"
    fi
    
    success "清理完成"
}

# 构建包
build() {
    info "构建包..."
    uv build
    
    # 显示构建产物
    echo ""
    info "构建产物:"
    ls -lh dist/
    success "构建完成"
}

# 检查构建产物
check() {
    info "检查构建产物..."
    
    if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
        error "dist/ 目录不存在或为空"
        exit 1
    fi
    
    # 使用 uvx 运行 twine check
    uvx twine check dist/*
    success "检查通过"
}

# 显示帮助
show_help() {
    echo "AuriMyth Foundation Kit - 打包工具"
    echo ""
    echo "使用方法: ./build.sh"
    echo ""
    echo "功能:"
    echo "  1. 检查 Git 状态和版本"
    echo "  2. 清理旧的构建文件"
    echo "  3. 构建包（wheel 和 source distribution）"
    echo "  4. 检查构建产物"
    echo ""
    echo "版本管理 (通过 Git 标签):"
    echo "  git tag v0.1.0          创建标签"
    echo "  git push --tags         推送标签"
    echo "  git tag -d v0.1.0       删除本地标签"
    echo ""
    echo "构建产物将保存在 dist/ 目录中"
}

# 主流程
main() {
    # 帮助信息
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        show_help
        exit 0
    fi
    
    echo ""
    echo "=========================================="
    echo "  AuriMyth Foundation Kit - 打包工具"
    echo "  使用 uv + hatch-vcs"
    echo "=========================================="
    echo ""
    
    check_uv
    check_git
    echo ""
    
    clean
    echo ""
    
    build
    echo ""
    
    check
    echo ""
    
    success "打包流程完成！"
    echo ""
    info "构建产物已保存在 dist/ 目录中"
    info "使用 ./publish.sh 发布到 PyPI"
}

main "$@"
