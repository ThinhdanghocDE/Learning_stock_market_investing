# Backend API - Learning Stock Market Investing

## 📋 Tổng Quan

Backend API được xây dựng với FastAPI theo mô hình MVC pattern.

## Cấu Trúc

```
backend/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── controllers/    # FastAPI route handlers
│   ├── services/        # Business logic
│   ├── repositories/    # Data access layer
│   ├── config.py        # Configuration
│   ├── database.py      # Database connections
│   └── main.py          # FastAPI app
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Environment Variables

Tạo file `.env` trong thư mục `backend/`:

```env
# Database - PostgreSQL (có thể dùng PG_* hoặc POSTGRES_*)
PG_HOST=localhost
PG_PORT=5432
PG_DB=stream_db
PG_USER=postgres
PG_PASSWORD=your_password

# Hoặc dùng POSTGRES_* (cũng được hỗ trợ)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=stream_db
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=your_password

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_DB=stock_db
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Debug
DEBUG=True
```

### 3. Chạy Server

```bash
# Development mode (với auto-reload)
python -m app.main

# Hoặc
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### **Authentication**

- `POST /api/auth/register` - Đăng ký user mới
- `POST /api/auth/login` - Đăng nhập và nhận JWT token
- `GET /api/auth/me` - Lấy thông tin user hiện tại (cần authentication)

### **Symbols**

- `GET /api/symbols` - Lấy danh sách symbols từ ClickHouse
  - Query params: `limit` (optional)

### **OHLC Data**

- `GET /api/ohlc/historical` - Lấy dữ liệu OHLC lịch sử
  - Query params: `symbol`, `start_time`, `end_time`, `interval`, `limit`
- `GET /api/ohlc/latest` - Lấy OHLC data mới nhất
  - Query params: `symbol`, `interval`, `limit`

### **Health Check**

- `GET /` - Root endpoint
- `GET /api/health` - Health check

## Authentication

API sử dụng JWT (JSON Web Tokens) cho authentication.

### **Đăng ký:**

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "email": "test@example.com"
  }'
```

### **Đăng nhập:**

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### **Sử dụng Token:**

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## API Documentation

Sau khi chạy server, truy cập:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Test

```bash
# Test health check
curl http://localhost:8000/api/health

# Test symbols
curl http://localhost:8000/api/symbols?limit=10

# Test OHLC data
curl "http://localhost:8000/api/ohlc/latest?symbol=VCB&limit=10"
```

## Next Steps

Xem [NEXT_STEPS_AFTER_DATA_COLLECTION.md](../docs/NEXT_STEPS_AFTER_DATA_COLLECTION.md) để biết các bước tiếp theo.

