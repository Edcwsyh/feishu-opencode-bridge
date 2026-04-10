import asyncio
import json
import logging
import os
import sys
import threading
import time
from typing import Optional, Dict, Any

import httpx
import lark_oapi as lark
from fastapi import FastAPI
from pydantic import BaseModel

from config import config

os.makedirs(config.LOG_DIR, exist_ok=True)
log_file = os.path.join(config.LOG_DIR, config.BRIDGE_LOG_FILE)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


class OpenCodeClient:
    def __init__(self, base_url: str, password: str = None):
        self.base_url = base_url.rstrip("/")
        self.password = password
        self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.password:
                import base64
                credentials = f"opencode:{self.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"
            self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=120.0)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def health(self) -> Dict[str, Any]:
        response = await self.client.get("/global/health")
        return {"data": response.json()}
    
    async def create_session(self, title: str = None) -> Dict[str, Any]:
        body = {"title": title} if title else {}
        response = await self.client.post("/session", json=body)
        data = response.json()
        return {"id": data.get("id"), **data}
    
    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        body = {"parts": [{"type": "text", "text": message}]}
        response = await self.client.post(f"/session/{session_id}/message", json=body)
        return response.json()


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, str] = {}
        self._opencode_client: Optional[OpenCodeClient] = None
    
    async def initialize(self, opencode_client):
        self._opencode_client = opencode_client
    
    async def get_or_create_session(self, user_id: str) -> str:
        if user_id in self._sessions:
            return self._sessions[user_id]
        
        session = await self._opencode_client.create_session(title=f"Feishu-{user_id}")
        session_id = session.get("id")
        if not session_id:
            raise Exception(f"创建 session 失败: {session}")
        
        self._sessions[user_id] = session_id
        logger.info(f"创建新 session: {session_id} for user: {user_id}")
        return session_id
    
    async def send_message(self, user_id: str, message: str) -> str:
        session_id = await self.get_or_create_session(user_id)
        result = await self._opencode_client.send_message(session_id, message)
        
        # 从 parts 中提取文本内容
        parts = result.get("parts", [])
        texts = []
        for part in parts:
            if part.get("type") == "text":
                text = part.get("text", "").strip()
                if text:
                    texts.append(text)
        
        if texts:
            return "\n\n".join(texts)
        
        # 备用：从 info 中提取
        info = result.get("info", {})
        if isinstance(info, dict):
            for key in ["content", "text"]:
                if info.get(key):
                    return info[key]
        return "处理完成"
    
    async def list_sessions(self) -> Dict[str, str]:
        return self._sessions.copy()


# 全局
opencode_client: Optional[OpenCodeClient] = None
session_manager = SessionManager()
feishu_client: Optional["FeishuClient"] = None
feishu_ws_client = None
processed_messages: set = set()  # 已处理的消息 ID，防止重复
MAX_PROCESSED_CACHE = 1000

# 持久化已处理消息 ID
PROCESSED_FILE = "/home/edcwsyh/work/feishu/processed_messages.json"

def load_processed_messages():
    """加载已处理的消息 ID"""
    try:
        import os
        if os.path.exists(PROCESSED_FILE):
            with open(PROCESSED_FILE, "r") as f:
                return set(json.load(f))
    except Exception as e:
        logger.warning(f"加载已处理消息失败: {e}")
    return set()

def save_processed_messages():
    """保存已处理的消息 ID"""
    try:
        with open(PROCESSED_FILE, "w") as f:
            json.dump(list(processed_messages), f)
    except Exception as e:
        logger.warning(f"保存已处理消息失败: {e}")

# 启动时加载
processed_messages = load_processed_messages()


class FeishuClient:
    """飞书客户端"""
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
    
    async def get_token(self) -> str:
        if self._token:
            return self._token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret}
            )
            data = response.json()
            if data.get("code") == 0:
                self._token = data["tenant_access_token"]
                return self._token
            raise Exception(f"获取 token 失败: {data}")
    
    async def send_message(self, receive_id: str, msg_type: str, content: str):
        token = await self.get_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={msg_type}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"receive_id": receive_id, "msg_type": "text", "content": json.dumps({"text": content})}
        
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json=payload)
    
    async def send_reply(self, message_id: str, content: str):
        token = await self.get_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"msg_type": "text", "content": json.dumps({"text": content})}
        
        async with httpx.AsyncClient() as client:
            await client.post(url, headers=headers, json=payload)
    
    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """获取消息详情"""
        token = await self.get_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("items", [{}])[0]
            raise Exception(f"获取消息失败: {data}")


async def get_message_content(message_id: str) -> str:
    """获取消息内容"""
    try:
        msg = await feishu_client.get_message(message_id)
        content = msg.get("body", {}).get("content", "")
        try:
            content_obj = json.loads(content)
            return content_obj.get("text", content)
        except:
            return content
    except Exception as e:
        logger.warning(f"获取消息 {message_id} 失败: {e}")
        return ""


def get_message_content_sync(message_id: str) -> str:
    """同步获取消息内容"""
    try:
        import requests
        # 获取 token
        token = feishu_client._token
        if not token:
            resp = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": config.FEISHU_APP_ID, "app_secret": config.FEISHU_APP_SECRET},
                timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                token = data["tenant_access_token"]
        
        resp = requests.get(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            if items:
                content = items[0].get("body", {}).get("content", "")
                try:
                    content_obj = json.loads(content)
                    return content_obj.get("text", content)
                except:
                    return content
        return ""
    except Exception as e:
        logger.warning(f"获取消息 {message_id} 失败: {e}")
        return ""


async def get_message_detail_async(message_id: str) -> dict:
    """通过 API 查询消息详情，获取 parent_id 等信息"""
    try:
        msg = await feishu_client.get_message(message_id)
        return {
            "parent_id": msg.get("parent_id", ""),
            "root_id": msg.get("root_id", ""),
            "content": msg.get("body", {}).get("content", "")
        }
    except Exception as e:
        logger.warning(f"查询消息详情 {message_id} 失败: {e}")
        return {}


def get_message_detail(message_id: str) -> dict:
    """同步获取消息详情"""
    import urllib.request
    import urllib.error
    
    try:
        # 获取 token
        token = feishu_client._token
        if not token:
            # 同步获取 token
            import requests
            resp = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": config.FEISHU_APP_ID, "app_secret": config.FEISHU_APP_SECRET},
                timeout=10
            )
            data = resp.json()
            if data.get("code") == 0:
                token = data["tenant_access_token"]
            else:
                return {}
        
        # 获取消息详情
        import requests
        resp = requests.get(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            if items:
                msg = items[0]
                return {
                    "parent_id": msg.get("parent_id", ""),
                    "root_id": msg.get("root_id", ""),
                    "content": msg.get("body", {}).get("content", "")
                }
        return {}
    except Exception as e:
        logger.warning(f"查询消息详情 {message_id} 失败: {e}")
        return {}


async def process_message(user_id: str, text: str, message_id: str):
    """处理消息"""
    try:
        logger.info(f"处理消息: user={user_id}, text={text[:50]}...")
        
        # 发送处理中提示
        await feishu_client.send_reply(message_id, "🤔 正在思考...")
        
        # 发送到 OpenCode
        response = await session_manager.send_message(user_id, text)
        
        # 截断过长响应
        max_length = 4000
        if len(response) > max_length:
            response = response[:max_length] + "\n\n...(响应过长已截断)"
        
        # 发送回复
        await feishu_client.send_reply(message_id, response)
        logger.info(f"消息处理完成")
        
    except Exception as e:
        logger.error(f"处理消息失败: {e}", exc_info=True)
        try:
            await feishu_client.send_reply(message_id, f"处理出错: {str(e)[:200]}")
        except:
            pass


def handle_feishu_event(data: dict):
    """处理飞书事件（长连接回调）"""
    try:
        logger.info(f"完整事件数据: {json.dumps(data, ensure_ascii=False)[:500]}")
        
        event = data.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        
        content = message.get("content", "{}")
        # 尝试从多个位置获取 parent_id
        parent_id = message.get("parent_id") or data.get("event", {}).get("message", {}).get("parent_id") or ""
        
        try:
            content_obj = json.loads(content)
        except:
            content_obj = {"text": content}
        
        text = content_obj.get("text", "").strip()
        
        user_id = sender.get("sender_id", {}).get("open_id", "")
        message_id = message.get("message_id", "")
        sender_type = sender.get("sender_type", "")
        create_time = message.get("create_time", 0)
        
        logger.info(f"消息详情 - message_id: {message_id}, parent_id: {parent_id}, root_id: {message.get('root_id')}, content: {content[:100]}")
        
        # 如果没有 parent_id，通过 API 查询消息详情获取
        actual_parent_id = parent_id
        if not actual_parent_id:
            try:
                msg_detail = get_message_detail(message_id)
                actual_parent_id = msg_detail.get("parent_id", "")
                logger.info(f"通过 API 查询到 parent_id: {actual_parent_id}")
            except Exception as e:
                logger.warning(f"查询消息详情失败: {e}")
        
        # 如果是引用回复，获取被引用消息的内容
        quoted_text = ""
        if actual_parent_id:
            logger.info(f"检测到引用消息, parent_id: {actual_parent_id}")
            try:
                quoted_text = get_message_content_sync(actual_parent_id)
                if quoted_text:
                    quoted_text = f"\n\n[引用消息]: {quoted_text}"
                    logger.info(f"获取到引用消息: {quoted_text[:100]}...")
            except Exception as e:
                logger.warning(f"获取引用消息失败: {e}")
        
        # 消息去重
        if message_id in processed_messages:
            logger.debug(f"忽略重复消息: {message_id}")
            return
        
        # 跳过太旧的消息（超过5分钟）
        current_time = int(time.time())
        if create_time > 0 and (current_time - create_time) > 300:
            logger.info(f"忽略历史消息: {message_id}")
            return
        
        logger.info(f"收到消息 - user: {user_id}, text: {text[:50]}, type: {sender_type}")
        
        # 忽略空消息或机器人消息
        if not text or sender_type == "bot":
            return
        
        # 标记消息为已处理并保存
        processed_messages.add(message_id)
        if len(processed_messages) > MAX_PROCESSED_CACHE:
            processed_messages.clear()
        save_processed_messages()
        
        # 组合消息文本（包含引用内容）
        full_text = text + quoted_text
        
        # 使用线程池执行异步任务
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, process_message(user_id, full_text, message_id))
            try:
                future.result(timeout=180)
            except Exception as e:
                logger.error(f"异步任务执行失败: {e}")
        
    except Exception as e:
        logger.error(f"处理飞书消息失败: {e}", exc_info=True)


app = FastAPI(title="飞书 OpenCode 桥接服务", version="1.0.0")


@app.on_event("startup")
async def startup():
    global opencode_client, feishu_client, feishu_ws_client
    
    logger.info("=" * 50)
    logger.info("启动飞书 OpenCode 桥接服务")
    logger.info("=" * 50)
    
    # 连接 OpenCode
    opencode_client = OpenCodeClient(config.OPENCODE_SERVER_URL, config.OPENCODE_SERVER_PASSWORD)
    await session_manager.initialize(opencode_client)
    health = await opencode_client.health()
    logger.info(f"OpenCode 连接成功: {health}")
    
    # 连接飞书长连接（需要企业自建应用）
    if config.FEISHU_APP_ID and config.FEISHU_APP_SECRET:
        try:
            feishu_client = FeishuClient(config.FEISHU_APP_ID, config.FEISHU_APP_SECRET)
            await feishu_client.get_token()  # 测试 token
            logger.info("飞书 API 连接成功")
            
            # 构建事件处理器
            from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder
            from lark_oapi.event.dispatcher_handler import P2ImMessageReceiveV1
            
            def on_im_message_receive_v1(data: P2ImMessageReceiveV1):
                try:
                    event_data = {
                        "event": {
                            "message": {
                                "message_id": data.event.message.message_id,
                                "content": data.event.message.content,
                                "chat_id": data.event.message.chat_id,
                                "msg_type": data.event.message.message_type
                            },
                            "sender": {
                                "sender_id": {"open_id": data.event.sender.sender_id.open_id},
                                "sender_type": data.event.sender.sender_type
                            }
                        }
                    }
                    handle_feishu_event(event_data)
                except Exception as e:
                    logger.error(f"处理飞书消息失败: {e}", exc_info=True)
            
            # 创建事件处理器并注册消息事件
            builder = EventDispatcherHandlerBuilder("", "")
            builder.register_p2_im_message_receive_v1(on_im_message_receive_v1)
            # 注册消息已读事件（忽略即可，防止报错）
            builder.register_p2_im_message_message_read_v1(lambda x: None)
            event_handler = builder.build()
            
            # 在后台线程中启动长连接
            def start_ws():
                ws_client = lark.ws.Client(
                    config.FEISHU_APP_ID,
                    config.FEISHU_APP_SECRET,
                    lark.LogLevel.INFO,
                    event_handler,
                    auto_reconnect=True
                )
                ws_client.start()
            
            ws_thread = threading.Thread(target=start_ws, daemon=True)
            ws_thread.start()
            logger.info("飞书长连接已启动（在线程中运行）")
        except Exception as e:
            logger.error(f"飞书连接失败: {e}", exc_info=True)
            logger.warning("请确保已配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    else:
        logger.warning("未配置飞书应用凭证，无法接收消息")


@app.on_event("shutdown")
async def shutdown():
    global opencode_client
    if opencode_client:
        await opencode_client.close()


@app.get("/")
async def root():
    return {"status": "running", "opencode_connected": opencode_client is not None}


@app.get("/health")
async def health():
    ok = False
    if opencode_client:
        try:
            ok = (await opencode_client.health()).get("data", {}).get("healthy", False)
        except:
            pass
    return {"status": "healthy" if ok else "degraded"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.HOST, port=config.PORT, reload=False)
