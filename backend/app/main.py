"""
FastAPI Main Application
Backend API cho hệ thống học và thực hành đầu tư chứng khoán
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env file từ thư mục root của project trước khi import app
# app/main.py -> app/ -> backend/ -> learning_stock_market_investing/
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Fallback: thử load từ thư mục backend/
    fallback_path = Path(__file__).parent.parent / ".env"
    if fallback_path.exists():
        load_dotenv(dotenv_path=fallback_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.config import settings
from app.controllers import auth_router, symbols_router, ohlc_router, lessons_router, portfolio_router
from app.controllers.websocket import router as websocket_router, start_ohlc_monitoring
from app.controllers.ai_coach import router as ai_coach_router
from app.database import Base, engine, ch_client
import logging
import asyncio
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tạo tables (chỉ trong development)
# Trong production, dùng Alembic migrations
try:
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified")
except Exception as e:
    logger.error(f"❌ Error creating tables: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager để start/stop background tasks"""
    # Startup: Start WebSocket monitoring task
    logger.info("🚀 Starting WebSocket OHLC monitoring...")
    try:
        monitoring_task = asyncio.create_task(start_ohlc_monitoring(ch_client, interval_seconds=5))
        logger.info("✅ WebSocket monitoring started")
    except Exception as e:
        logger.error(f"❌ Error starting WebSocket monitoring: {e}")
        monitoring_task = None
    
    yield
    
    # Shutdown: Cancel monitoring task
    if monitoring_task:
        logger.info("🛑 Shutting down WebSocket monitoring...")
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        logger.info("✅ WebSocket monitoring stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="API cho hệ thống học và thực hành đầu tư chứng khoán",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Exception handler cho validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production, chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(symbols_router)
app.include_router(ohlc_router)
app.include_router(lessons_router)
app.include_router(portfolio_router)
app.include_router(websocket_router)
app.include_router(ai_coach_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.DEBUG)

