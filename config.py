import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")
    FEISHU_APP_ID: str = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET: str = os.getenv("FEISHU_APP_SECRET", "")
    OPENCODE_SERVER_URL: str = os.getenv("OPENCODE_SERVER_URL", "http://localhost:4096")
    OPENCODE_SERVER_PASSWORD: str = os.getenv("OPENCODE_SERVER_PASSWORD", "")
    PORT: int = int(os.getenv("PORT", "8080"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
