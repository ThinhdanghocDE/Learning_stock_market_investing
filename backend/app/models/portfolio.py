"""
Portfolio Models
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Portfolio(Base):
    """Portfolio model"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    cash_balance = Column(Numeric(15, 2), default=1000000.00, nullable=False)  # 1M VND - Tổng tiền mặt
    blocked_cash = Column(Numeric(15, 2), default=0.00, nullable=False)  # Tiền bị phong tỏa (từ QUEUED/PENDING orders)
    total_value = Column(Numeric(15, 2), default=1000000.00, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def available_cash(self):
        """Tiền khả dụng = cash_balance - blocked_cash"""
        return self.cash_balance - self.blocked_cash
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    
    def __repr__(self):
        return f"<Portfolio(user_id={self.user_id}, cash={self.cash_balance}, total={self.total_value})>"


class VirtualOrder(Base):
    """Virtual Order model"""
    __tablename__ = "virtual_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY, SELL
    order_type = Column(String(10), default="MARKET", nullable=False)  # MARKET, LIMIT, ATO, ATC
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=True)  # NULL nếu MARKET order, NULL cho ATO/ATC (sẽ fill sau)
    status = Column(String(20), default="PENDING", nullable=False, index=True)  # PENDING, QUEUED, FILLED, CANCELLED, REJECTED
    trading_mode = Column(String(20), default="REALTIME", nullable=False)  # REALTIME, PRACTICE
    execution_time = Column(DateTime(timezone=True), nullable=True)  # Thời điểm thực thi (cho PRACTICE mode)
    filled_quantity = Column(Integer, default=0, nullable=False)
    filled_price = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="check_side"),
        CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'ATO', 'ATC')", name="check_order_type"),
        CheckConstraint("status IN ('PENDING', 'QUEUED', 'FILLED', 'CANCELLED', 'REJECTED')", name="check_status"),
        CheckConstraint("trading_mode IN ('REALTIME', 'PRACTICE')", name="check_trading_mode"),
    )
    
    def __repr__(self):
        return f"<VirtualOrder(id={self.id}, user_id={self.user_id}, symbol={self.symbol}, side={self.side}, status={self.status})>"


class VirtualPosition(Base):
    """Virtual Position model"""
    __tablename__ = "virtual_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Numeric(10, 2), nullable=False)
    unrealized_pnl = Column(Numeric(15, 2), default=0.00, nullable=False)
    last_price = Column(Numeric(10, 2), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="positions")
    
    def __repr__(self):
        return f"<VirtualPosition(user_id={self.user_id}, symbol={self.symbol}, quantity={self.quantity}, avg_price={self.avg_price})>"

