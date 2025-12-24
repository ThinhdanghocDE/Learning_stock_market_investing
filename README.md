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

## Cấu Trúc Thư Mục

```
learning_stock_market_investing/
├── backend/                  # Backend API (FastAPI)
│   ├── app/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── controllers/     # FastAPI route handlers
│   │   ├── services/        # Business logic
│   │   ├── repositories/    # Data access layer
│   │   └── main.py         # FastAPI app
│   └── requirements.txt
│
├── data_collectors/          # Scripts thu thập dữ liệu
│   ├── dnse.py              # Real-time ticks từ DNSE
│   ├── download_vnstock_latest.py  # Historical data từ Vnstock
│   ├── fetch_dnse_symbols.py       # Lấy danh sách symbols
│   └── check_vnstock_symbols.py    # Kiểm tra symbols
│
├── websocket/               # WebSocket server
│   ├── websocket_server.py  # WebSocket server cho real-time
│   └── test_websocket_client.html  # Test client
│
├── frontend/                # Frontend (sẽ phát triển)
│   └── index.html
│
├── docs/                    # Tài liệu
│   ├── SYSTEM_ARCHITECTURE_SOLUTION.md
│   ├── NEXT_STEPS_AFTER_DATA_COLLECTION.md
│   └── ...
│
├── sql/                     # SQL scripts
│   └── *.sql
│
└── README.md
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

## Tài Liệu

- [System Architecture Solution](docs/SYSTEM_ARCHITECTURE_SOLUTION.md)
- [Next Steps After Data Collection](docs/NEXT_STEPS_AFTER_DATA_COLLECTION.md)
- [VNStock to ClickHouse Migration](docs/VNSTOCK_TO_CLICKHOUSE_MIGRATION.md)

## Công Nghệ Sử Dụng

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL, ClickHouse
- **Real-time**: WebSocket
- **Data Collection**: DNSE API, Vnstock API
- **Frontend**: TradingView Lightweight Charts (sẽ phát triển)

## Roadmap

Xem [NEXT_STEPS_AFTER_DATA_COLLECTION.md](docs/NEXT_STEPS_AFTER_DATA_COLLECTION.md) để biết các bước tiếp theo.

## Đóng Góp

1. Fork project
2. Tạo feature branch
3. Commit changes
4. Push và tạo Pull Request

## License

MIT License

