# 飞书 OpenCode 桥接服务

将 OpenCode 接入飞书机器人，实现通过飞书与 OpenCode 对话。

## 功能特性

- **飞书长连接接收消息**：实时接收飞书消息，支持 @ 机器人对话
- **多消息类型支持**：
  - 文本消息
  - 图片消息
  - 富文本消息
  - 合并转发消息
  - 引用回复（自动获取上下文）
- **会话管理**：为每个用户创建独立会话，自动保持上下文
- **可配置工作目录**：支持指定 OpenCode 工作目录
- **可配置默认 Agent**：支持指定默认使用的 Agent

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置

复制配置模板并填写：

```bash
cp .env.template .env
```

编辑 `.env` 文件，配置以下内容：

| 配置项 | 说明 |
|--------|------|
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `OPENCODE_SERVER_URL` | OpenCode Server 地址（默认 `http://localhost:4096`） |
| `OPENCODE_SERVER_PASSWORD` | OpenCode Server 密码（可选） |
| `WORKING_DIR` | OpenCode 工作目录（如 `~/work`） |
| `DEFAULT_AGENT` | 默认 Agent 名称（如 `coder`） |

### 3. 启动服务

```bash
./start.sh
```

服务启动后会显示：
- OpenCode Server: http://localhost:4096
- 桥接服务: http://localhost:8080

### 4. 停止服务

```bash
./stop.sh
```

## 飞书应用配置

1. 前往 [飞书开放平台](https://open.feishu.cn/) 创建企业自建应用
2. 开启 **机器人能力**
3. 配置 **权限**：
   - `im:message`：获取与发送单聊、群组消息
   - `im:message:send_as_bot`：以应用的身份发消息
4. 开启 **长连接** 接收消息模式
5. 将 App ID 和 App Secret 填入 `.env` 文件

## 项目结构

```
feishu-opencode-bridge/
├── app.py              # 桥接服务主程序
├── config.py           # 配置加载
├── requirements.txt    # Python 依赖
├── start.sh           # 启动脚本
├── stop.sh            # 停止脚本
├── setup.sh           # 配置初始化脚本
├── .env               # 实际配置（不提交）
└── .env.template      # 配置模板
```

## 日志

日志默认保存在 `/tmp/$USER/feishu-opencode-bridge/` 目录：

- `opencode.log`：OpenCode Server 日志
- `bridge.log`：桥接服务日志

## 支持的消息类型

| 类型 | 说明 |
|------|------|
| 文本 | 直接提取文本内容 |
| 图片 | 显示 `[用户发送了一张图片: image_key]` |
| 富文本 | 提取标题和文本内容 |
| 合并转发 | 解析子消息内容 |
| 引用回复 | 自动获取被引用消息内容作为上下文 |

## 开发

### 运行测试

```bash
python3 app.py
```

### 健康检查

```bash
curl http://localhost:8080/health
```

## License

MIT
