#!/bin/bash

# 飞书 OpenCode 桥接服务启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  飞书 OpenCode 桥接服务${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: .env 文件不存在${NC}"
    echo ""
    echo -e "请先运行 ${YELLOW}./setup.sh${NC} 进行配置"
    echo ""
    exit 1
fi

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
pip3 show fastapi > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}安装依赖...${NC}"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}依赖安装失败${NC}"
        exit 1
    fi
fi

# 杀掉旧的进程
echo -e "${YELLOW}清理旧进程...${NC}"
pkill -f "python3 app.py" 2>/dev/null
pkill -f "opencode serve" 2>/dev/null
sleep 1

# 启动 OpenCode Server
echo -e "${GREEN}启动 OpenCode Server...${NC}"
nohup opencode serve --port 4096 > /tmp/opencode.log 2>&1 &
OPENCODE_PID=$!
echo "OpenCode Server PID: $OPENCODE_PID"

# 等待 OpenCode Server 启动
sleep 3

# 检查 OpenCode Server 是否启动成功
if ! curl -s http://localhost:4096/global/health > /dev/null 2>&1; then
    echo -e "${RED}OpenCode Server 启动失败${NC}"
    echo "查看日志: tail -f /tmp/opencode.log"
    exit 1
fi

echo -e "${GREEN}OpenCode Server 启动成功${NC}"

# 启动桥接服务
echo ""
echo -e "${GREEN}启动飞书桥接服务...${NC}"
nohup python3 app.py > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
echo "桥接服务 PID: $BRIDGE_PID"

# 等待桥接服务启动
sleep 3

# 检查桥接服务是否启动成功
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${RED}桥接服务启动失败${NC}"
    echo "查看日志: tail -f /tmp/bridge.log"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  服务启动成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "OpenCode Server: ${BLUE}http://localhost:4096${NC}"
echo -e "桥接服务:         ${BLUE}http://localhost:8080${NC}"
echo ""
echo -e "查看日志:"
echo -e "  OpenCode: ${YELLOW}tail -f /tmp/opencode.log${NC}"
echo -e "  桥接服务: ${YELLOW}tail -f /tmp/bridge.log${NC}"
echo ""
echo -e "停止服务: ${YELLOW}pkill -f \"opencode serve\" && pkill -f \"python3 app.py\"${NC}"
echo ""
echo -e "${YELLOW}现在可以在飞书中 @机器人 发送消息了！${NC}"
echo ""

# 保持运行
wait
