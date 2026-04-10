#!/bin/bash

# 飞书 OpenCode 桥接服务设置脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
TEMPLATE_FILE="$SCRIPT_DIR/.env.template"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  飞书 OpenCode 桥接服务设置"
echo "========================================"
echo ""

# 检查是否已存在 .env 文件
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}.env 文件已存在，是否重新配置？${NC}"
    read -p "输入 y 重新配置，其他键跳过: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "跳过配置。"
        exit 0
    fi
fi

# 检查模板文件
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}错误: 找不到 .env.template 文件${NC}"
    exit 1
fi

# 复制模板
cp "$TEMPLATE_FILE" "$ENV_FILE"

echo ""
echo -e "${GREEN}已创建 .env 文件${NC}"
echo ""
echo "请编辑 .env 文件，填写以下配置:"
echo ""
echo "1. FEISHU_APP_ID - 飞书应用的 App ID"
echo "2. FEISHU_APP_SECRET - 飞书应用的 App Secret"
echo ""
echo "获取方式:"
echo "1. 打开 https://open.feishu.cn/app"
echo "2. 创建或选择你的应用"
echo "3. 在「凭证与基础信息」中获取 App ID 和 App Secret"
echo ""
echo -e "${YELLOW}提示: 编辑完成后，运行 ./start.sh 启动服务${NC}"
echo ""

# 尝试打开编辑器
if command -v code &> /dev/null; then
    read -p "是否用 VS Code 打开 .env 文件? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        code "$ENV_FILE"
    fi
fi
