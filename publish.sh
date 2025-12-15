#!/bin/bash

# AuriMyth Foundation Kit - PyPI 发布脚本（使用 uv）
#
# 使用方法:
#   ./publish.sh [test|prod]
#
# 参数说明:
#   test: 发布到测试 PyPI (https://test.pypi.org)
#   prod: 发布到正式 PyPI (https://pypi.org) - 默认
#
# 前置条件:
#   需要先运行 ./build.sh 构建包，或确保 dist/ 目录存在
#
# Token 配置 (PyPI 已不支持密码登录，必须使用 API Token):
#   方式 1: 环境变量 UV_PUBLISH_TOKEN
#   方式 2: keyring set https://upload.pypi.org/legacy/ __token__

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 默认参数
TARGET="${1:-prod}"

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

# 检查构建产物
check_dist() {
    info "检查构建产物..."
    
    if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
        error "dist/ 目录不存在或为空"
        echo ""
        warning "请先运行 ./build.sh 构建包"
        exit 1
    fi
    
    # 检查文件是否存在
    WHEEL_FILE=$(ls dist/*.whl 2>/dev/null | head -n 1)
    SDIST_FILE=$(ls dist/*.tar.gz 2>/dev/null | head -n 1)
    
    if [ -z "$WHEEL_FILE" ]; then
        error "未找到 wheel 文件 (.whl)"
        warning "请先运行 ./build.sh 构建包"
        exit 1
    fi
    
    if [ -z "$SDIST_FILE" ]; then
        error "未找到源码分发文件 (.tar.gz)"
        warning "请先运行 ./build.sh 构建包"
        exit 1
    fi
    
    info "找到构建产物:"
    echo "  - Wheel: $(basename "$WHEEL_FILE")"
    echo "  - Source: $(basename "$SDIST_FILE")"
}

# 配置 Token
setup_token() {
    if [ -z "$UV_PUBLISH_TOKEN" ]; then
        # 尝试从 pypi_key 文件读取
        if [ -f "pypi_key" ]; then
            info "从 pypi_key 文件读取 token..."
            export UV_PUBLISH_TOKEN="$(cat pypi_key | tr -d '\n')"
        else
            warning "未设置 UV_PUBLISH_TOKEN 环境变量，也未找到 pypi_key 文件"
            info "Token 配置方式 (PyPI 必须使用 API Token):"
            echo "  1. 环境变量: export UV_PUBLISH_TOKEN='pypi-xxxx...'"
            echo "  2. 创建 pypi_key 文件: echo 'your-token' > pypi_key"
            echo "  3. keyring: keyring set https://upload.pypi.org/legacy/ __token__"
            echo ""
            info "获取 Token: https://pypi.org/manage/account/token/"
            echo ""
            read -p "是否继续? (yes/no): " continue_confirm
            if [ "$continue_confirm" != "yes" ]; then
                info "已取消发布"
                exit 0
            fi
        fi
    fi
}

# 发布
publish() {
    local pypi_name pypi_url
    
    if [ "$TARGET" = "test" ]; then
        pypi_name="测试 PyPI (test.pypi.org)"
        pypi_url="https://test.pypi.org/legacy/"
    else
        pypi_name="正式 PyPI (pypi.org)"
        pypi_url=""
    fi
    
    echo ""
    echo "=========================================="
    warning "即将发布到 $pypi_name"
    echo "=========================================="
    echo ""
    info "构建产物:"
    ls -lh dist/
    echo ""
    
    read -p "确认发布? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        info "已取消发布"
        exit 0
    fi
    
    info "开始上传..."
    # 构建 uv publish 命令
    local publish_cmd="uv publish"
    
    if [ "$TARGET" = "test" ]; then
        publish_cmd="$publish_cmd --publish-url '$pypi_url'"
    fi
    
    # 添加认证信息（优先使用 token）
    if [ -n "$UV_PUBLISH_TOKEN" ]; then
        publish_cmd="$publish_cmd --token '$UV_PUBLISH_TOKEN'"
    fi
    
    # 执行发布命令
    eval "$publish_cmd"
    
    success "发布完成！"
    echo ""
    if [ "$TARGET" = "test" ]; then
        echo "测试安装命令:"
        echo "  uv add --index-url https://test.pypi.org/simple/ aury-boot"
    else
        echo "安装命令:"
        echo "  uv add aury-boot"
    fi
}

# 显示帮助
show_help() {
    echo "AuriMyth Foundation Kit - PyPI 发布工具"
    echo ""
    echo "使用方法: ./publish.sh [test|prod]"
    echo ""
    echo "参数:"
    echo "  test    发布到测试 PyPI"
    echo "  prod    发布到正式 PyPI (默认)"
    echo ""
    echo "前置条件:"
    echo "  需要先运行 ./build.sh 构建包，或确保 dist/ 目录存在"
    echo ""
    echo "Token 配置 (PyPI 必须使用 API Token):"
    echo "  方式 1: 环境变量"
    echo "    export UV_PUBLISH_TOKEN='pypi-xxxx...'"
    echo ""
    echo "  方式 2: 创建 pypi_key 文件"
    echo "    echo 'your-token' > pypi_key"
    echo ""
    echo "  方式 3: keyring"
    echo "    keyring set https://upload.pypi.org/legacy/ __token__"
    echo ""
    echo "获取 Token: https://pypi.org/manage/account/token/"
}

# 主流程
main() {
    # 帮助信息
    if [ "$TARGET" = "-h" ] || [ "$TARGET" = "--help" ]; then
        show_help
        exit 0
    fi
    
    # 验证参数
    if [ "$TARGET" != "test" ] && [ "$TARGET" != "prod" ]; then
        error "无效参数: $TARGET"
        echo "使用 ./publish.sh --help 查看帮助"
        exit 1
    fi
    
    echo ""
    echo "=========================================="
    echo "  AuriMyth Foundation Kit - PyPI 发布"
    echo "  使用 uv + hatch-vcs"
    echo "=========================================="
    echo ""
    
    if [ "$TARGET" = "test" ]; then
        info "目标: ${YELLOW}测试 PyPI${NC}"
    else
        info "目标: ${GREEN}正式 PyPI${NC}"
    fi
    echo ""
    
    check_uv
    echo ""
    
    check_dist
    echo ""
    
    setup_token
    echo ""
    
    publish
    
    echo ""
    success "发布流程完成！"
}

main
