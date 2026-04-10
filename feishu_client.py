import httpx
import logging
from typing import Optional
from config import config

logger = logging.getLogger(__name__)


class FeishuClient:
    def __init__(self):
        self.webhook_url = config.FEISHU_WEBHOOK_URL
        self.app_id = config.FEISHU_APP_ID
        self.app_secret = config.FEISHU_APP_SECRET
        self._tenant_access_token: Optional[str] = None
    
    async def send_text_message(self, receive_id: str, msg_type: str, content: str) -> dict:
        """通过飞书开放接口发送消息"""
        if not self.app_id or not self.app_secret:
            logger.warning("未配置飞书应用凭证，使用 Webhook 方式发送")
            return await self.send_webhook_message(content)
        
        # 获取 tenant_access_token
        token = await self._get_tenant_access_token()
        
        # 发送消息 API
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={msg_type}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": content
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            result = response.json()
            logger.info(f"发送消息响应: {result}")
            return result
    
    async def send_webhook_message(self, content: str) -> dict:
        """通过 Webhook 发送消息（机器人）"""
        if not self.webhook_url:
            logger.error("未配置飞书 Webhook URL")
            return {"code": -1, "msg": "未配置 Webhook URL"}
        
        payload = {
            "msg_type": "text",
            "content": {"text": content}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json=payload)
            result = response.json()
            logger.info(f"Webhook 消息发送响应: {result}")
            return result
    
    async def send_reply(self, message_id: str, content: str) -> dict:
        """回复消息"""
        token = await self._get_tenant_access_token()
        
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "msg_type": "text",
            "content": content
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()
    
    async def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._tenant_access_token:
            return self._tenant_access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                self._tenant_access_token = result["tenant_access_token"]
                return self._tenant_access_token
            else:
                raise Exception(f"获取 token 失败: {result}")
    
    def parse_message(self, event_data: dict) -> dict:
        """解析飞书事件数据"""
        message = event_data.get("message", {})
        sender = event_data.get("sender", {})
        
        return {
            "message_id": message.get("message_id"),
            "chat_id": message.get("chat_id"),
            "content": message.get("content", ""),
            "msg_type": message.get("msg_type"),
            "sender_id": sender.get("sender_id", {}).get("open_id"),
            "sender_type": sender.get("sender_type"),
        }


feishu_client = FeishuClient()
