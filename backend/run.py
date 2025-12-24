"""
Script để chạy Backend API
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file từ thư mục root của project
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    fallback_path = Path(__file__).parent / ".env"
    if fallback_path.exists():
        load_dotenv(dotenv_path=fallback_path)

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("🚀 Starting Backend API...")
    print(f"   Host: 0.0.0.0")
    print(f"   Port: 8000")
    print(f"   Reload: {settings.DEBUG}")
    print(f"   Environment: {'Development' if settings.DEBUG else 'Production'}")
    print()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        reload_includes=["*.py"],  # Reload khi có thay đổi file .py
        reload_excludes=["*.pyc", "__pycache__"]  # Bỏ qua cache files
    )

