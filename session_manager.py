import asyncio
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    user_id: str
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time)


class SessionManager:
    """会话管理器 - 管理用户与 OpenCode session 的映射"""
    
    def __init__(self):
        # user_id -> session_id
        self._sessions: Dict[str, str] = {}
        self._opencode_client = None
    
    async def initialize(self, opencode_client):
        """初始化 OpenCode 客户端"""
        self._opencode_client = opencode_client
        logger.info("SessionManager 初始化完成")
    
    async def get_or_create_session(self, user_id: str) -> str:
        """获取或创建用户的 session"""
        if user_id in self._sessions:
            session_id = self._sessions[user_id]
            logger.info(f"复用已有 session: {session_id} for user: {user_id}")
            return session_id
        
        # 创建新 session
        try:
            session = await self._opencode_client.create_session(
                title=f"Feishu-{user_id}"
            )
            session_id = session.get("id")
            if not session_id:
                raise Exception(f"创建 session 失败，未返回 id: {session}")
            
            self._sessions[user_id] = session_id
            logger.info(f"创建新 session: {session_id} for user: {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"创建 session 失败: {e}")
            raise
    
    async def send_message(self, user_id: str, message: str) -> str:
        """发送消息到 OpenCode 并获取响应"""
        session_id = await self.get_or_create_session(user_id)
        
        try:
            result = await self._opencode_client.send_message(session_id, message)
            
            # 解析响应
            # 响应格式: {"info": {...}, "parts": [...]}
            if result and isinstance(result, dict):
                # 尝试从 info 中提取文本
                info = result.get("info", {})
                if isinstance(info, dict):
                    # 尝试多种可能的文本字段
                    content = info.get("content", "")
                    if content:
                        return content
                    
                    text = info.get("text", "")
                    if text:
                        return text
                    
                    # 尝试 message 字段
                    message_data = info.get("message", {})
                    if message_data:
                        return str(message_data)
                    
                    # 返回整个 info
                    return str(info)
                
                return str(result)
            
            return "处理完成"
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise
    
    async def abort_session(self, user_id: str) -> bool:
        """中止用户的 session"""
        if user_id not in self._sessions:
            return False
        
        try:
            session_id = self._sessions[user_id]
            await self._opencode_client.abort_session(session_id)
            return True
        except Exception as e:
            logger.error(f"中止 session 失败: {e}")
            return False
    
    async def list_sessions(self) -> Dict[str, str]:
        """列出所有会话"""
        return self._sessions.copy()
    
    async def clear_session(self, user_id: str) -> bool:
        """清除用户的 session"""
        if user_id in self._sessions:
            del self._sessions[user_id]
            logger.info(f"清除 session for user: {user_id}")
            return True
        return False


# 全局实例
session_manager = SessionManager()
