"""
OHLC Data Controllers
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_clickhouse
from app.repositories.clickhouse_repository import ClickHouseRepository

router = APIRouter(prefix="/api/ohlc", tags=["OHLC Data"])


@router.get("/historical")
async def get_ohlc_historical(
    symbol: str = Query(..., description="Mã chứng khoán"),
    start_time: Optional[datetime] = Query(None, description="Thời gian bắt đầu"),
    end_time: Optional[datetime] = Query(None, description="Thời gian kết thúc"),
    interval: str = Query("1m", description="Interval: 1m, 5m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=10000, description="Giới hạn số lượng records"),
    ch_client = Depends(get_clickhouse)
):
    """Lấy dữ liệu OHLC lịch sử từ ClickHouse"""
    # Default: 7 ngày gần nhất
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=7)
    
    # Validate interval
    valid_intervals = ["1m", "5m", "1h", "1d"]
    if interval not in valid_intervals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interval. Must be one of: {valid_intervals}"
        )
    
    repo = ClickHouseRepository(ch_client)
    data = repo.get_ohlc_historical(
        symbol=symbol,
        start_time=start_time,
        end_time=end_time,
        interval=interval,
        limit=limit
    )
    
    return {
        "symbol": symbol,
        "interval": interval,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "count": len(data),
        "data": data
    }


@router.get("/latest")
async def get_latest_ohlc(
    symbol: str = Query(..., description="Mã chứng khoán"),
    interval: str = Query("1m", description="Interval: 1m, 5m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Giới hạn số lượng records"),
    ch_client = Depends(get_clickhouse)
):
    """Lấy OHLC data mới nhất"""
    repo = ClickHouseRepository(ch_client)
    data = repo.get_latest_ohlc(symbol=symbol, interval=interval, limit=limit)
    
    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(data),
        "data": data
    }

