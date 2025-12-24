# Learning Stock Market Investing Platform

Hệ thống học và thực hành đầu tư chứng khoán với AI, sử dụng dữ liệu real-time và lịch sử từ DNSE và Vnstock.

## Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                           │
│  - TradingView Charts (Historical + Live)                   │
│  - AI Side-panel (Chat)                                     │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND API (FastAPI)                      │
│  - REST API (Users, Lessons, Portfolio, Orders)            │
│  - WebSocket Server (Real-time updates)                    │
│  - AI Coach Service                                         │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  - ClickHouse (Market Data: ticks, ohlc, symbols)          │
│  - PostgreSQL (Business Data: users, lessons, portfolio)   │
└─────────────────────────────────────────────────────────────┘
```

## Bắt Đầu

### 1. Setup Environment

```bash
# Copy .env.example và điền thông tin
cp .env.example .env

# Chỉnh sửa .env với thông tin database của bạn
```

### 2. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt
```

### 3. Setup Database

```bash
# Chạy PostgreSQL và ClickHouse (Docker)
docker-compose -f docker-compose-clickhouse.yml up -d

# Chạy SQL scripts để tạo tables
# Xem trong thư mục sql/
```

### 4. Chạy Data Collectors

```bash
# Thu thập symbols
python data_collectors/fetch_dnse_symbols.py

# Thu thập dữ liệu lịch sử
python data_collectors/download_vnstock_latest.py

# Thu thập dữ liệu real-time (chạy background)
python data_collectors/dnse.py
```

### 5. Chạy Backend API

```bash
cd backend
python -m app.main

# Hoặc
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Chạy WebSocket Server

```bash
python websocket/websocket_server.py
```

## Công Nghệ Sử Dụng

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL, ClickHouse
- **Real-time**: WebSocket
- **Data Collection**: DNSE API, Vnstock API
- **Frontend**: TradingView Lightweight Charts (sẽ phát triển)


