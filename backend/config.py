import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value


class Settings:
    GEMINI_API_KEY: str = _env("GEMINI_API_KEY")
    GEMINI_MODEL: str = _env("GEMINI_MODEL", "gemini-2.5-flash")
    MONGO_URL: str = _env("MONGO_URL", "mongodb://localhost:27017/chatbot_db")
    
    JWT_SECRET_KEY: str = _env("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = _env("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    
    def __init__(self):
        # Validate critical environment variables
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set in environment variables")
        if not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY must be set in environment variables. Generate one with: openssl rand -hex 32")
    
    SMTP_HOST: str = _env("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(_env("SMTP_PORT", "587"))
    SMTP_USER: str = _env("SMTP_USER")
    SMTP_PASSWORD: str = _env("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = _env("SMTP_FROM_EMAIL")
    SMTP_FROM_NAME: str = _env("SMTP_FROM_NAME", "Gemini Chatbot")
    SMTP_MOCK_MODE: bool = _env("SMTP_MOCK_MODE", "false").lower() == "true"
    
    CORS_ORIGINS: list = [origin.strip() for origin in _env("CORS_ORIGINS", "*").split(",") if origin.strip()]
    
    MAX_HISTORY_LIMIT: int = int(_env("MAX_HISTORY_LIMIT", "5"))
    NOTIFICATION_POLL_INTERVAL: int = int(_env("NOTIFICATION_POLL_INTERVAL", "10"))
    
    RATE_LIMIT_MAX_RETRIES: int = int(_env("RATE_LIMIT_MAX_RETRIES", "3"))
    RATE_LIMIT_BACKOFF_BASE: int = int(_env("RATE_LIMIT_BACKOFF_BASE", "5"))


settings = Settings()
