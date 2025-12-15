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
    rm -rf build/ dist/ *.egg-info aury/*.egg-info aury/foundation_kit/_version.py
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
