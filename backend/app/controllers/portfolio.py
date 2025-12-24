"""
Portfolio Controllers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db, get_clickhouse
from app.schemas.portfolio import (
    PortfolioResponse, VirtualOrderCreate, VirtualOrderResponse,
    VirtualPositionResponse, PortfolioSummary
)
from app.repositories.portfolio_repository import (
    PortfolioRepository, VirtualOrderRepository, VirtualPositionRepository
)
from app.services.trading_service import TradingService
from app.controllers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy portfolio của user"""
    portfolio = PortfolioRepository.get_or_create_portfolio(db, current_user.id)
    return portfolio


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """Lấy portfolio summary với positions và giá real-time"""
    summary = TradingService.get_portfolio_summary(db, current_user.id, ch_client)
    return summary


@router.get("/positions", response_model=List[VirtualPositionResponse])
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Lấy tất cả positions của user với giá real-time
    
    Lưu ý: Positions chỉ được tạo khi orders FILLED.
    Nếu thấy positions không hợp lệ, có thể do dữ liệu cũ. Chạy cleanup script để xóa.
    """
    # Tự động check và fill QUEUED MARKET orders nếu đang trong giờ giao dịch
    # (Ngoài giờ giao dịch không có giá real-time, nên không fill được)
    TradingService.check_and_fill_queued_market_orders(db, user_id=current_user.id, ch_client=ch_client)
    # Tự động check và fill LIMIT orders khi giá đạt mức giới hạn
    TradingService.check_and_fill_limit_orders(db, user_id=current_user.id, ch_client=ch_client)
    
    # Validate positions: chỉ lấy positions có order FILLED tương ứng
    from sqlalchemy import func
    from app.models.portfolio import VirtualOrder
    
    all_positions = VirtualPositionRepository.get_all_by_user(db, current_user.id)
    valid_positions = []
    
    for position in all_positions:
        # Tính expected quantity từ orders FILLED
        buy_quantity = db.query(func.sum(VirtualOrder.quantity)).filter(
            VirtualOrder.user_id == current_user.id,
            VirtualOrder.symbol == position.symbol,
            VirtualOrder.side == "BUY",
            VirtualOrder.status == "FILLED"
        ).scalar() or 0
        
        sell_quantity = db.query(func.sum(VirtualOrder.quantity)).filter(
            VirtualOrder.user_id == current_user.id,
            VirtualOrder.symbol == position.symbol,
            VirtualOrder.side == "SELL",
            VirtualOrder.status == "FILLED"
        ).scalar() or 0
        
        expected_quantity = buy_quantity - sell_quantity
        
        # Chỉ trả về position nếu quantity khớp với orders FILLED
        if position.quantity == expected_quantity and expected_quantity > 0:
            valid_positions.append(position)
        else:
            # Log warning nếu có position không hợp lệ
            print(f"⚠️  Invalid position detected: User {current_user.id}, {position.symbol}, "
                  f"quantity={position.quantity}, expected={expected_quantity}")
    
    # Update với giá real-time
    for position in valid_positions:
        current_price = TradingService.get_current_price(ch_client, position.symbol)
        if current_price:
            VirtualPositionRepository.update_position_price(db, position, current_price)
    
    return valid_positions


@router.post("/reset-balance")
async def reset_portfolio_balance(
    initial_balance: float = Query(..., description="Số tiền ban đầu (VND)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset portfolio balance về một giá trị ban đầu
    Dùng cho challenge mode hoặc reset portfolio
    """
    from decimal import Decimal
    
    portfolio = PortfolioRepository.get_or_create_portfolio(db, current_user.id)
    
    # Set cash balance và total value
    PortfolioRepository.set_cash_balance(db, portfolio, Decimal(str(initial_balance)))
    
    return {
        "message": "Portfolio balance reset successfully",
        "cash_balance": float(portfolio.cash_balance),
        "total_value": float(portfolio.total_value)
    }


@router.post("/add-balance")
async def add_portfolio_balance(
    amount: float = Query(..., description="Số tiền cần thêm (VND)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Thêm balance vào portfolio hiện tại
    """
    from decimal import Decimal
    
    portfolio = PortfolioRepository.get_or_create_portfolio(db, current_user.id)
    
    # Thêm amount vào balance hiện tại
    PortfolioRepository.update_cash_balance(db, portfolio, Decimal(str(amount)))
    
    # Update total value
    portfolio.total_value = portfolio.cash_balance
    db.commit()
    db.refresh(portfolio)
    
    return {
        "message": "Balance added successfully",
        "cash_balance": float(portfolio.cash_balance),
        "total_value": float(portfolio.total_value),
        "amount_added": amount
    }


@router.get("/orders", response_model=List[VirtualOrderResponse])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, description="Filter by status: PENDING, QUEUED, FILLED, CANCELLED, REJECTED"),
    trading_mode_filter: Optional[str] = Query(None, description="Filter by trading mode: REALTIME, PRACTICE"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy lịch sử orders của user"""
    orders = VirtualOrderRepository.get_by_user(db, current_user.id, skip=skip, limit=limit)
    
    if status_filter:
        orders = [o for o in orders if o.status == status_filter.upper()]
    
    if trading_mode_filter:
        orders = [o for o in orders if o.trading_mode == trading_mode_filter.upper()]
    
    return orders


@router.post("/orders", response_model=VirtualOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: VirtualOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Tạo order mới (buy/sell)
    
    - REALTIME mode: Kiểm tra giờ giao dịch (9:00-11:30, 13:00-15:00, Thứ 2-6)
      - Trong giờ: MARKET orders sẽ được fill ngay
      - Ngoài giờ: Orders sẽ ở status QUEUED
    - PRACTICE mode: Không kiểm tra giờ giao dịch, fill ngay
    """
    order, error = TradingService.create_order(db, current_user.id, order_data, ch_client)
    if error and order is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    # Nếu có error nhưng order đã được tạo (QUEUED), vẫn trả về order nhưng có thể log warning
    return order


@router.delete("/orders/{order_id}", response_model=VirtualOrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hủy order"""
    order, error = TradingService.cancel_order(db, current_user.id, order_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    return order


@router.get("/orders/{order_id}", response_model=VirtualOrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy chi tiết order"""
    order = VirtualOrderRepository.get_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order


@router.post("/update-value")
async def update_portfolio_value(
    as_of_date: Optional[str] = Query(None, description="Thời điểm tính toán (YYYY-MM-DD HH:MM:SS). None = real-time"),
    simulation: bool = Query(False, description="Simulation mode: không cập nhật DB, chỉ tính toán"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Cập nhật portfolio value
    
    - Real-time mode (as_of_date=None): Cập nhật với giá hiện tại
    - Simulation mode (as_of_date có giá trị): Tính toán tại thời điểm cụ thể, không cập nhật DB
    """
    as_of_datetime = None
    if as_of_date:
        try:
            as_of_datetime = datetime.strptime(as_of_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                as_of_datetime = datetime.strptime(as_of_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
                )
    
    result = TradingService.update_portfolio_value(
        db, 
        current_user.id, 
        ch_client, 
        as_of_date=as_of_datetime,
        update_db=not simulation
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # result là dict với thông tin chi tiết
    return {
        "total_value": float(result["total_value"]),
        "cash_balance": float(result["cash_balance"]),
        "total_positions_value": float(result["total_positions_value"]),
        "total_unrealized_pnl": float(result["total_unrealized_pnl"]),
        "as_of_date": as_of_date,
        "simulation": simulation
    }


@router.post("/check-limit-orders")
async def check_limit_orders(
    as_of_date: Optional[str] = Query(None, description="Thời điểm check (YYYY-MM-DD HH:MM:SS). None = real-time"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Kiểm tra và fill các LIMIT orders khi giá đạt mức giới hạn
    
    - Chỉ check orders của user hiện tại
    - BUY LIMIT: fill khi giá <= limit_price
    - SELL LIMIT: fill khi giá >= limit_price
    """
    as_of_datetime = None
    if as_of_date:
        try:
            as_of_datetime = datetime.strptime(as_of_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                as_of_datetime = datetime.strptime(as_of_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
                )
    
    result = TradingService.check_and_fill_limit_orders(
        db,
        user_id=current_user.id,
        ch_client=ch_client,
        as_of_date=as_of_datetime
    )
    
    return result


@router.post("/check-queued-orders")
async def check_queued_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ch_client = Depends(get_clickhouse)
):
    """
    Kiểm tra và fill các QUEUED MARKET orders khi vào giờ giao dịch
    
    - Chỉ check orders của user hiện tại
    - Chỉ fill nếu đang trong giờ giao dịch (9:00-11:30, 13:00-15:00, Thứ 2-6)
    - Ngoài giờ giao dịch không có giá real-time, nên không thể fill
    - MARKET orders sẽ được fill với giá hiện tại khi vào giờ giao dịch
    """
    result = TradingService.check_and_fill_queued_market_orders(
        db,
        user_id=current_user.id,
        ch_client=ch_client
    )
    
    return result


@router.post("/cleanup-invalid-positions")
async def cleanup_invalid_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Xóa các positions không hợp lệ (không có order FILLED tương ứng)
    
    Positions chỉ được tạo khi orders FILLED. Nếu có positions không hợp lệ,
    có thể do dữ liệu cũ từ trước khi sửa logic.
    """
    from sqlalchemy import func
    from app.models.portfolio import VirtualOrder, VirtualPosition
    
    all_positions = VirtualPositionRepository.get_all_by_user(db, current_user.id)
    invalid_positions = []
    
    for position in all_positions:
        # Tính expected quantity từ orders FILLED
        buy_quantity = db.query(func.sum(VirtualOrder.quantity)).filter(
            VirtualOrder.user_id == current_user.id,
            VirtualOrder.symbol == position.symbol,
            VirtualOrder.side == "BUY",
            VirtualOrder.status == "FILLED"
        ).scalar() or 0
        
        sell_quantity = db.query(func.sum(VirtualOrder.quantity)).filter(
            VirtualOrder.user_id == current_user.id,
            VirtualOrder.symbol == position.symbol,
            VirtualOrder.side == "SELL",
            VirtualOrder.status == "FILLED"
        ).scalar() or 0
        
        expected_quantity = buy_quantity - sell_quantity
        
        # Nếu quantity không khớp hoặc expected = 0 nhưng position vẫn tồn tại
        if position.quantity != expected_quantity or (expected_quantity == 0 and position.quantity > 0):
            invalid_positions.append({
                "position": position,
                "expected": expected_quantity,
                "actual": position.quantity
            })
    
    # Xóa invalid positions
    deleted_count = 0
    for item in invalid_positions:
        position = item["position"]
        db.delete(position)
        deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Đã xóa {deleted_count} positions không hợp lệ",
        "deleted_count": deleted_count,
        "details": [
            {
                "symbol": item["position"].symbol,
                "actual_quantity": item["actual"],
                "expected_quantity": item["expected"]
            }
            for item in invalid_positions
        ]
    }
