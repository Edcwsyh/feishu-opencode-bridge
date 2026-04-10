#!/bin/bash

# 停止飞书 OpenCode 桥接服务

echo "停止服务..."

pkill -f "python3 app.py" 2>/dev/null && echo "桥接服务已停止"
pkill -f "opencode serve" 2>/dev/null && echo "OpenCode Server 已停止"

echo "完成"
