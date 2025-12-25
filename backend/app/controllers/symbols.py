"""
Symbols Controllers
"""

from fastapi import APIRouter, Depends, Query
from app.database import get_clickhouse
from app.repositories.clickhouse_repository import ClickHouseRepository

router = APIRouter(prefix="/api/symbols", tags=["Symbols"])


@router.get("")
async def get_symbols(
    limit: int = Query(None, ge=1, le=10000, description="Giới hạn số lượng symbols (None = không giới hạn)"),
    ch_client = Depends(get_clickhouse)
):
    """Lấy danh sách symbols từ ClickHouse"""
    repo = ClickHouseRepository(ch_client)
    symbols = repo.get_symbols(limit=limit)
    return {
        "count": len(symbols),
        "symbols": symbols
    }


@router.get("/popular")
async def get_popular_symbols(
    limit: int = Query(10, ge=1, le=50, description="Số lượng mã trả về"),
    interval: str = Query("1m", description="Interval của nến: 1m, 5m, 1h, 1d"),
    min_candles: int = Query(100, ge=1, description="Số nến tối thiểu"),
    ch_client = Depends(get_clickhouse)
):
    """
    Lấy danh sách các mã chứng khoán có nhiều nến nhất
    Sắp xếp theo số lượng nến giảm dần
    """
    repo = ClickHouseRepository(ch_client)
    top_symbols = repo.get_top_symbols_by_candle_count(
        interval=interval,
        limit=limit,
        min_candles=min_candles
    )
    return {
        "count": len(top_symbols),
        "interval": interval,
        "symbols": top_symbols
    }


@router.get("/{symbol}")
async def get_symbol_info(
    symbol: str,
    ch_client = Depends(get_clickhouse)
):
    """
    Lấy thông tin chi tiết của một symbol
    """
    repo = ClickHouseRepository(ch_client)
    info = repo.get_symbol_info(symbol.upper())
    
    if info:
        return {"data": info}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
