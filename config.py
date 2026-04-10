import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LOG_DIR = f"/tmp/{os.environ.get('USER', 'root')}/feishu-opencode-bridge"


class Config:
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
    OPENCODE_SERVER_URL: str = os.getenv("OPENCODE_SERVER_URL", "http://localhost:4096")
    OPENCODE_SERVER_PASSWORD: str = os.getenv("OPENCODE_SERVER_PASSWORD", "")
    PORT: int = int(os.getenv("PORT", "8080"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.path.expanduser(os.getenv("LOG_DIR", DEFAULT_LOG_DIR))
    OPENCODE_LOG_FILE: str = os.getenv("OPENCODE_LOG_FILE", "opencode.log")
    BRIDGE_LOG_FILE: str = os.getenv("BRIDGE_LOG_FILE", "bridge.log")
    DEFAULT_AGENT: str = os.getenv("DEFAULT_AGENT", "")
    WORKING_DIR: str = os.path.expanduser(os.getenv("WORKING_DIR", ""))


config = Config()
