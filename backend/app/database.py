"""
Database connections: PostgreSQL và ClickHouse
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env file từ thư mục root của project trước khi import config
# app/database.py -> app/ -> backend/ -> learning_stock_market_investing/
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback: thử load từ thư mục backend/
    fallback_path = Path(__file__).parent.parent / ".env"
    if fallback_path.exists():
        load_dotenv(dotenv_path=fallback_path)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from clickhouse_driver import Client as CHClient
from app.config import settings

# ============================================================
# PostgreSQL (SQLAlchemy)
# ============================================================

engine = create_engine(
    settings.postgres_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# ClickHouse
# ============================================================

ch_client = CHClient(
    host=settings.CLICKHOUSE_HOST,
    port=settings.CLICKHOUSE_PORT,
    database=settings.CLICKHOUSE_DB,
    user=settings.CLICKHOUSE_USER,
    password=settings.CLICKHOUSE_PASSWORD
)


def get_clickhouse():
    """Dependency để lấy ClickHouse client"""
    return ch_client

