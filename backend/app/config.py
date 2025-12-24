"""
Configuration settings cho Backend API
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# Load .env file từ thư mục root của project (learning_stock_market_investing/)
# backend/app/config.py -> backend/ -> learning_stock_market_investing/
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback: thử load từ thư mục backend/
    fallback_path = Path(__file__).parent.parent / ".env"
    if fallback_path.exists():
        load_dotenv(dotenv_path=fallback_path)


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Learning Stock Market Investing API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database - PostgreSQL
    # Hỗ trợ cả PG_* và POSTGRES_* để tương thích
    POSTGRES_HOST: str = os.getenv("PG_HOST") or os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("PG_PORT") or os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("PG_DB") or os.getenv("POSTGRES_DB", "stream_db")
    POSTGRES_USER: str = os.getenv("PG_USER") or os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("PG_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
    
    # Database - ClickHouse
    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "stock_db")
    CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # WebSocket
    WEBSOCKET_HOST: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "8765"))
    
    # LLM API (Optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

