"""
Portfolio Repository - Data Access Layer
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from app.models.portfolio import Portfolio, VirtualOrder, VirtualPosition
from app.schemas.portfolio import VirtualOrderCreate
from typing import List, Optional
from decimal import Decimal


class PortfolioRepository:
    """Portfolio repository"""
    
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Optional[Portfolio]:
        """Lấy portfolio của user"""
        return db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    
    @staticmethod
    def create_portfolio(db: Session, user_id: int, initial_balance: Decimal = Decimal("1000000.00")) -> Portfolio:
        """Tạo portfolio mới cho user"""
        portfolio = Portfolio(
            user_id=user_id,
            cash_balance=initial_balance,
            total_value=initial_balance
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    def get_or_create_portfolio(db: Session, user_id: int) -> Portfolio:
        """Lấy hoặc tạo portfolio cho user"""
        portfolio = PortfolioRepository.get_by_user_id(db, user_id)
        if not portfolio:
            portfolio = PortfolioRepository.create_portfolio(db, user_id)
        return portfolio
    
    @staticmethod
    def update_cash_balance(db: Session, portfolio: Portfolio, amount: Decimal) -> Portfolio:
        """Cập nhật cash balance"""
        portfolio.cash_balance += amount
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    def set_cash_balance(db: Session, portfolio: Portfolio, amount: Decimal) -> Portfolio:
        """Set cash balance về một giá trị cụ thể"""
        portfolio.cash_balance = amount
        portfolio.total_value = amount  # Reset total value khi set cash balance
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    def update_total_value(db: Session, portfolio: Portfolio, total_value: Decimal) -> Portfolio:
        """Cập nhật total value"""
        portfolio.total_value = total_value
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    def block_cash(db: Session, portfolio: Portfolio, amount: Decimal) -> Portfolio:
        """Block (phong tỏa) tiền cho QUEUED/PENDING orders"""
        portfolio.blocked_cash += amount
        db.commit()
        db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    def unblock_cash(db: Session, portfolio: Portfolio, amount: Decimal) -> Portfolio:
        """Unblock (giải phóng) tiền đã bị phong tỏa"""
        portfolio.blocked_cash -= amount
        if portfolio.blocked_cash < 0:
            portfolio.blocked_cash = Decimal("0")  # Không cho phép âm
        db.commit()
        db.refresh(portfolio)
        return portfolio


class VirtualOrderRepository:
    """Virtual Order repository"""
    
    @staticmethod
    def create(db: Session, user_id: int, order_data: VirtualOrderCreate, status: str = "PENDING") -> VirtualOrder:
        """Tạo order mới"""
        order = VirtualOrder(
            user_id=user_id,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=order_data.quantity,
            price=order_data.price,
            trading_mode=order_data.trading_mode,
            execution_time=order_data.execution_time,
            status=status
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_by_id(db: Session, order_id: int) -> Optional[VirtualOrder]:
        """Lấy order theo ID"""
        return db.query(VirtualOrder).filter(VirtualOrder.id == order_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[VirtualOrder]:
        """Lấy danh sách orders của user"""
        return db.query(VirtualOrder).filter(
            VirtualOrder.user_id == user_id
        ).order_by(desc(VirtualOrder.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_pending_orders(db: Session, user_id: int, symbol: Optional[str] = None) -> List[VirtualOrder]:
        """Lấy danh sách pending/queued orders"""
        query = db.query(VirtualOrder).filter(
            and_(
                VirtualOrder.user_id == user_id,
                VirtualOrder.status.in_(["PENDING", "QUEUED"])
            )
        )
        if symbol:
            query = query.filter(VirtualOrder.symbol == symbol)
        return query.order_by(VirtualOrder.created_at).all()
    
    @staticmethod
    def get_pending_limit_orders(db: Session, user_id: Optional[int] = None, symbol: Optional[str] = None) -> List[VirtualOrder]:
        """Lấy danh sách LIMIT orders đang pending/queued"""
        query = db.query(VirtualOrder).filter(
            and_(
                VirtualOrder.order_type == "LIMIT",
                VirtualOrder.status.in_(["PENDING", "QUEUED"])
            )
        )
        if user_id:
            query = query.filter(VirtualOrder.user_id == user_id)
        if symbol:
            query = query.filter(VirtualOrder.symbol == symbol)
        return query.order_by(VirtualOrder.created_at).all()
    
    @staticmethod
    def get_queued_market_orders(db: Session, user_id: Optional[int] = None) -> List[VirtualOrder]:
        """Lấy danh sách QUEUED MARKET orders (chỉ REALTIME mode)"""
        query = db.query(VirtualOrder).filter(
            and_(
                VirtualOrder.order_type == "MARKET",
                VirtualOrder.status == "QUEUED",
                VirtualOrder.trading_mode == "REALTIME"
            )
        )
        if user_id:
            query = query.filter(VirtualOrder.user_id == user_id)
        return query.order_by(VirtualOrder.created_at).all()
    
    @staticmethod
    def fill_order(
        db: Session,
        order: VirtualOrder,
        filled_quantity: int,
        filled_price: Decimal
    ) -> VirtualOrder:
        """Fill order"""
        from datetime import datetime
        order.status = "FILLED"
        order.filled_quantity = filled_quantity
        order.filled_price = filled_price
        order.filled_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def cancel_order(db: Session, order: VirtualOrder) -> VirtualOrder:
        """Cancel order"""
        from datetime import datetime
        order.status = "CANCELLED"
        order.cancelled_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def reject_order(db: Session, order: VirtualOrder, reason: Optional[str] = None) -> VirtualOrder:
        """Reject order"""
        order.status = "REJECTED"
        db.commit()
        db.refresh(order)
        return order


class VirtualPositionRepository:
    """Virtual Position repository"""
    
    @staticmethod
    def get_by_user_and_symbol(db: Session, user_id: int, symbol: str) -> Optional[VirtualPosition]:
        """Lấy position của user cho symbol"""
        return db.query(VirtualPosition).filter(
            and_(
                VirtualPosition.user_id == user_id,
                VirtualPosition.symbol == symbol
            )
        ).first()
    
    @staticmethod
    def get_all_by_user(db: Session, user_id: int) -> List[VirtualPosition]:
        """Lấy tất cả positions của user"""
        return db.query(VirtualPosition).filter(
            VirtualPosition.user_id == user_id
        ).all()
    
    @staticmethod
    def create_or_update_position(
        db: Session,
        user_id: int,
        symbol: str,
        quantity_change: int,
        price: Decimal
    ) -> VirtualPosition:
        """Tạo hoặc cập nhật position"""
        position = VirtualPositionRepository.get_by_user_and_symbol(db, user_id, symbol)
        
        if position:
            # Update existing position
            if position.quantity + quantity_change == 0:
                # Position closed, delete it
                db.delete(position)
                db.commit()
                return None
            else:
                # Update average price và quantity
                total_cost = (position.quantity * position.avg_price) + (quantity_change * price)
                position.quantity += quantity_change
                position.avg_price = total_cost / position.quantity
        else:
            # Create new position
            if quantity_change == 0:
                return None
            position = VirtualPosition(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity_change,
                avg_price=price
            )
            db.add(position)
        
        db.commit()
        db.refresh(position)
        return position
    
    @staticmethod
    def update_position_price(
        db: Session,
        position: VirtualPosition,
        current_price: Decimal
    ) -> VirtualPosition:
        """Cập nhật giá hiện tại và unrealized P&L"""
        position.last_price = current_price
        # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính P&L (để ra VNĐ)
        position.unrealized_pnl = (current_price - position.avg_price) * position.quantity * Decimal("1000")
        db.commit()
        db.refresh(position)
        return position

