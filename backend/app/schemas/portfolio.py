"""
Portfolio Schemas (Pydantic)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PortfolioBase(BaseModel):
    """Base portfolio schema"""
    cash_balance: Decimal = Field(default=1000000.00, description="Số tiền mặt tổng (VND)")
    blocked_cash: Decimal = Field(default=0.00, description="Tiền bị phong tỏa từ QUEUED/PENDING orders (VND)")
    total_value: Decimal = Field(default=1000000.00, description="Tổng giá trị portfolio")


class PortfolioResponse(PortfolioBase):
    """Schema để trả về portfolio"""
    id: int
    user_id: int
    updated_at: datetime
    available_cash: Decimal = Field(..., description="Tiền khả dụng = cash_balance - blocked_cash")
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }
    
    @classmethod
    def from_orm(cls, obj):
        """Override để tính available_cash"""
        # Tính available_cash từ model property
        available = obj.available_cash if hasattr(obj, 'available_cash') else (obj.cash_balance - obj.blocked_cash)
        data = super().from_orm(obj)
        data.available_cash = available
        return data


class VirtualOrderBase(BaseModel):
    """Base virtual order schema"""
    symbol: str = Field(..., max_length=10, description="Mã chứng khoán")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="BUY hoặc SELL")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$", description="MARKET hoặc LIMIT")
    quantity: int = Field(..., gt=0, description="Số lượng")
    price: Optional[Decimal] = Field(None, description="Giá (bắt buộc nếu LIMIT order)")
    trading_mode: str = Field(default="REALTIME", pattern="^(REALTIME|PRACTICE)$", description="REALTIME hoặc PRACTICE")
    execution_time: Optional[datetime] = Field(None, description="Thời điểm thực thi order (chỉ cho PRACTICE mode). None = thời điểm hiện tại")


class VirtualOrderCreate(VirtualOrderBase):
    """Schema để tạo order mới"""
    current_price: Optional[Decimal] = Field(None, description="Giá hiện tại từ chart (frontend gửi lên, ưu tiên dùng giá này)")


class VirtualOrderResponse(VirtualOrderBase):
    """Schema để trả về order"""
    id: int
    user_id: int
    status: str = Field(..., description="PENDING, QUEUED, FILLED, CANCELLED, REJECTED")
    filled_quantity: int = Field(default=0)
    filled_price: Optional[Decimal] = None
    created_at: datetime
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class VirtualPositionBase(BaseModel):
    """Base virtual position schema"""
    symbol: str = Field(..., max_length=10)
    quantity: int = Field(..., description="Số lượng đang nắm giữ")
    avg_price: Decimal = Field(..., description="Giá trung bình")
    unrealized_pnl: Decimal = Field(default=0.00, description="Lãi/lỗ chưa thực hiện")
    last_price: Optional[Decimal] = None


class VirtualPositionResponse(VirtualPositionBase):
    """Schema để trả về position"""
    id: int
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class PortfolioSummary(BaseModel):
    """Schema để trả về portfolio summary"""
    portfolio: PortfolioResponse
    positions: List[VirtualPositionResponse]
    total_positions_value: Decimal = Field(..., description="Tổng giá trị positions")
    total_unrealized_pnl: Decimal = Field(..., description="Tổng lãi/lỗ chưa thực hiện")


class OrderBookEntry(BaseModel):
    """Schema cho order book entry"""
    symbol: str
    side: str  # BUY hoặc SELL
    price: Decimal
    quantity: int
    order_id: int
    created_at: datetime

