"""
Trading Service - Business Logic cho Virtual Trading
"""

from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional, Tuple, Dict
from datetime import datetime
from app.repositories.portfolio_repository import PortfolioRepository, VirtualOrderRepository, VirtualPositionRepository
from app.repositories.clickhouse_repository import ClickHouseRepository
from app.services.trading_hours_service import TradingHoursService
from app.models.portfolio import VirtualOrder
from app.schemas.portfolio import VirtualOrderCreate


class TradingService:
    """Trading service"""
    
    @staticmethod
    def validate_order(
        db: Session,
        user_id: int,
        order_data: VirtualOrderCreate,
        current_price: Optional[Decimal] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate order trước khi tạo
        Returns: (is_valid, error_message)
        """
        portfolio = PortfolioRepository.get_or_create_portfolio(db, user_id)
        
        # Validate LIMIT order có price (ATO/ATC không cần price vì sẽ fill sau)
        if order_data.order_type == "LIMIT" and not order_data.price:
            return False, "LIMIT order requires price"
        
        # Validate BUY order có đủ tiền
        # ATO/ATC: Không validate balance ngay vì giá chưa biết, sẽ validate khi fill
        # Trong PRACTICE mode, không validate balance vì đây là mode thực hành với số dư ảo
        if order_data.side == "BUY" and order_data.trading_mode != "PRACTICE" and order_data.order_type not in ["ATO", "ATC"]:
            # Xác định giá để tính toán
            price_to_use = order_data.price if order_data.price else current_price
            if not price_to_use:
                return False, "Cannot determine price for order validation"
            
            # Giá từ ClickHouse là nghìn VNĐ (23.55 = 23,550 VNĐ), cần nhân 1000 khi tính tiền
            total_cost = price_to_use * order_data.quantity * Decimal("1000")
            available_cash = portfolio.cash_balance - portfolio.blocked_cash
            print(f"DEBUG validate_order: order_type={order_data.order_type}, price={price_to_use}, quantity={order_data.quantity}, total_cost={total_cost}, cash_balance={portfolio.cash_balance}, blocked_cash={portfolio.blocked_cash}, available_cash={available_cash}")
            
            if available_cash < total_cost:
                return False, f"Insufficient balance. Required: {total_cost}, Available: {available_cash}, Total: {portfolio.cash_balance}, Blocked: {portfolio.blocked_cash}"
        
        # Validate SELL order có đủ shares
        elif order_data.side == "SELL":
            position = VirtualPositionRepository.get_by_user_and_symbol(
                db, user_id, order_data.symbol
            )
            if not position or position.quantity < order_data.quantity:
                available = position.quantity if position else 0
                return False, f"Insufficient shares. Required: {order_data.quantity}, Available: {available}"
        
        return True, None
    
    @staticmethod
    def get_current_price(
        ch_client,
        symbol: str,
        as_of_date: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """
        Lấy giá từ ClickHouse
        - Nếu as_of_date=None: Lấy giá hiện tại (real-time) - candle mới nhất
        - Nếu as_of_date có giá trị: Lấy giá tại thời điểm đó (simulation)
        """
        try:
            repo = ClickHouseRepository(ch_client)
            if as_of_date:
                # Lấy giá tại thời điểm cụ thể (simulation mode)
                price = repo.get_price_at_time(symbol, as_of_date, interval="1m")
                if price is not None:
                    return Decimal(str(price))
            else:
                # Lấy giá hiện tại (real-time) - candle mới nhất
                latest_data = repo.get_latest_ohlc(symbol, interval="1m", limit=1)
                if latest_data and len(latest_data) > 0:
                    latest_candle = latest_data[0]  # Candle đầu tiên là mới nhất (ORDER BY time DESC)
                    price = latest_candle.get("close")
                    if price is not None:
                        print(f"DEBUG get_current_price: symbol={symbol}, time={latest_candle.get('time')}, close={price}")
                        return Decimal(str(price))
                    else:
                        print(f"WARNING get_current_price: symbol={symbol}, latest candle has no close price")
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            import traceback
            traceback.print_exc()
        return None
    
    @staticmethod
    def create_order(
        db: Session,
        user_id: int,
        order_data: VirtualOrderCreate,
        ch_client
    ) -> Tuple[Optional[VirtualOrder], Optional[str]]:
        """
        Tạo order mới
        Returns: (order, error_message)
        """
        # Validate execution_time (chỉ cho PRACTICE mode)
        if order_data.execution_time and order_data.trading_mode != "PRACTICE":
            return None, "execution_time chỉ được dùng với PRACTICE mode"
        
        # Xác định thời điểm lấy giá
        price_time = order_data.execution_time if order_data.execution_time else None
        
        # PRACTICE mode: luôn có thể trade, không cần kiểm tra giờ giao dịch
        is_practice_mode = order_data.trading_mode == "PRACTICE"
        
        # Kiểm tra giờ giao dịch (chỉ cho REALTIME mode, không kiểm tra nếu có execution_time)
        can_trade = True
        trade_error = None
        if not order_data.execution_time:  # Chỉ kiểm tra nếu không có execution_time (real-time)
            can_trade, trade_error = TradingHoursService.can_trade_now(order_data.trading_mode)
        
        # Get price nếu MARKET order (ATO/ATC không cần giá ngay, sẽ fill sau)
        # Ưu tiên dùng giá từ frontend (current_price từ chart - giá mới nhất real-time)
        # Chỉ fallback về get_current_price nếu không có
        current_price = None
        if order_data.order_type == "MARKET":
            # Ưu tiên 1: Dùng giá từ frontend (chart) - giá mới nhất real-time
            if order_data.current_price:
                current_price = Decimal(str(order_data.current_price))
                print(f"DEBUG create_order: Using current_price from frontend (chart): {current_price}")
            # Fallback: Lấy từ ClickHouse
            elif is_practice_mode:
                # PRACTICE mode: Thử lấy giá tại execution_time trước (nếu có)
                if price_time:
                    current_price = TradingService.get_current_price(ch_client, order_data.symbol, as_of_date=price_time)
                # Nếu không có giá tại execution_time, lấy giá mới nhất từ ClickHouse
                if not current_price:
                    current_price = TradingService.get_current_price(ch_client, order_data.symbol, as_of_date=None)
                    print(f"DEBUG create_order: Using current_price from ClickHouse (PRACTICE fallback): {current_price}")
            else:
                # REALTIME mode: lấy giá từ ClickHouse (fallback nếu frontend không gửi)
                current_price = TradingService.get_current_price(ch_client, order_data.symbol, as_of_date=price_time)
                print(f"DEBUG create_order: Using current_price from ClickHouse (REALTIME fallback): {current_price}")
            
            print(f"DEBUG create_order: MARKET order, symbol={order_data.symbol}, trading_mode={order_data.trading_mode}, is_practice={is_practice_mode}, price_time={price_time}, current_price={current_price}, quantity={order_data.quantity}")
            
            if not current_price:
                time_str = price_time.strftime("%Y-%m-%d %H:%M:%S") if price_time else "hiện tại"
                return None, f"Could not get price for {order_data.symbol} at {time_str}"
        
        # Validate order (ATO/ATC không cần validate balance ngay vì giá chưa biết)
        is_valid, error = TradingService.validate_order(db, user_id, order_data, current_price)
        if not is_valid:
            return None, error
        
        # Với MARKET orders, nếu không có price từ order_data, lưu current_price vào order.price
        # Điều này đảm bảo order có price trong DB để tính blocked cash và fill order sau này
        # ATO/ATC: price = NULL (sẽ fill sau)
        order_price = order_data.price
        if order_data.order_type == "MARKET" and not order_price and current_price:
            order_price = current_price
            print(f"DEBUG create_order: MARKET order without price, using current_price: {current_price}")
        
        # Tạo order_data với price đã được set (nếu cần)
        from app.schemas.portfolio import VirtualOrderCreate
        order_data_with_price = VirtualOrderCreate(
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=order_data.quantity,
            price=order_price,  # Sử dụng price đã được set (có thể là current_price cho MARKET orders)
            trading_mode=order_data.trading_mode,
            execution_time=order_data.execution_time,
            current_price=order_data.current_price  # Giữ lại current_price từ frontend nếu có
        )
        
        # Xác định status ban đầu
        initial_status = "PENDING"
        
        # ATO/ATC: Luôn PENDING, không fill ngay
        if order_data.order_type in ["ATO", "ATC"]:
            initial_status = "PENDING"
        elif not can_trade and order_data.trading_mode == "REALTIME":
            # Ngoài giờ giao dịch → QUEUED (chỉ cho REALTIME)
            initial_status = "QUEUED"
        elif can_trade and order_data.order_type == "MARKET" and order_data.trading_mode == "REALTIME":
            # Trong giờ giao dịch và MARKET order → sẽ fill ngay
            initial_status = "PENDING"  # Sẽ được fill ngay sau
        
        # Create order với price đã được set
        order = VirtualOrderRepository.create(db, user_id, order_data_with_price, status=initial_status)
        
        # Auto-fill MARKET orders (không fill ATO/ATC):
        # - PRACTICE mode: LUÔN fill ngay (bỏ qua can_trade hoàn toàn)
        # - REALTIME mode: chỉ fill nếu trong giờ giao dịch (can_trade = True)
        should_fill = False
        if order_data.order_type == "MARKET":
            if is_practice_mode:
                # PRACTICE mode: luôn fill ngay, không cần kiểm tra can_trade
                should_fill = True
            elif can_trade:
                # REALTIME mode: chỉ fill nếu trong giờ giao dịch
                should_fill = True
        
        if should_fill:
            # Fill ngay, không cần block tiền
            fill_price = current_price
            order, fill_error = TradingService.fill_order(db, order.id, fill_price, ch_client)
            if fill_error:
                return None, fill_error
        else:
            # Không fill ngay → Block tiền cho BUY orders ở trạng thái QUEUED/PENDING (chỉ REALTIME mode)
            # ATO/ATC: Không block tiền ngay vì giá chưa biết, sẽ validate khi fill
            # PRACTICE mode không block vì là số dư ảo
            if order.side == "BUY" and order.status in ["QUEUED", "PENDING"] and order.trading_mode == "REALTIME" and order_data.order_type not in ["ATO", "ATC"]:
                portfolio = PortfolioRepository.get_or_create_portfolio(db, user_id)
                # Xác định giá để tính toán blocked amount
                block_price = order.price if order.price else current_price
                if block_price:
                    # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
                    blocked_amount = block_price * order.quantity * Decimal("1000")
                    PortfolioRepository.block_cash(db, portfolio, blocked_amount)
                    print(f"✅ Blocked {blocked_amount} VNĐ for order {order.id} (status: {order.status})")
        
        # Nếu không thể trade ngay (chỉ cho REALTIME mode), trả về thông báo
        if not can_trade and not is_practice_mode:
            next_session = TradingHoursService.get_next_trading_session()
            next_session_str = next_session.strftime("%Y-%m-%d %H:%M:%S") if next_session else "N/A"
            return order, f"Order đã được tạo với status QUEUED. {trade_error}. Phiên giao dịch tiếp theo: {next_session_str}"
        
        return order, None
    
    @staticmethod
    def fill_order(
        db: Session,
        order_id: int,
        fill_price: Decimal,
        ch_client = None
    ) -> Tuple[Optional[VirtualOrder], Optional[str]]:
        """
        Fill order với giá cụ thể
        Returns: (order, error_message)
        """
        order = VirtualOrderRepository.get_by_id(db, order_id)
        if not order:
            return None, "Order not found"
        
        if order.status not in ["PENDING", "QUEUED"]:
            return None, f"Cannot fill order with status {order.status}"
        
        portfolio = PortfolioRepository.get_or_create_portfolio(db, order.user_id)
        
        # Validate lại TRƯỚC KHI fill (vì có thể tình trạng đã thay đổi từ khi tạo order)
        if order.side == "BUY":
            # Validate BUY: Check available cash (sau khi unblock)
            # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
            total_cost = fill_price * order.quantity * Decimal("1000")
            if order.trading_mode == "REALTIME":
                # Tính blocked amount sẽ được unblock
                blocked_amount = (order.price if order.price else fill_price) * order.quantity * Decimal("1000")
                # Available cash sau khi unblock = cash_balance - (blocked_cash - blocked_amount)
                available_after_unblock = portfolio.cash_balance - (portfolio.blocked_cash - blocked_amount)
                if available_after_unblock < total_cost:
                    return None, f"Insufficient balance to fill order. Required: {total_cost}, Available after unblock: {available_after_unblock}"
        else:  # SELL
            # Validate SELL: Check position có đủ shares không
            position = VirtualPositionRepository.get_by_user_and_symbol(
                db, order.user_id, order.symbol
            )
            if not position or position.quantity < order.quantity:
                available = position.quantity if position else 0
                return None, f"Insufficient shares to fill order. Required: {order.quantity}, Available: {available}"
        
        # Fill order
        order = VirtualOrderRepository.fill_order(db, order, order.quantity, fill_price)
        
        # Update portfolio và positions
        if order.side == "BUY":
            # Unblock tiền (nếu đã block) và trừ tiền, thêm position
            # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
            total_cost = fill_price * order.quantity * Decimal("1000")
            
            # Unblock tiền nếu order đã bị block (QUEUED/PENDING)
            if order.trading_mode == "REALTIME":
                # Tính blocked amount: 
                # - LIMIT order: dùng order.price (giá giới hạn)
                # - MARKET order: dùng fill_price (giá khớp thực tế)
                # Lưu ý: Nếu order.price có giá trị, đó là giá đã block ban đầu
                # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
                blocked_amount = (order.price if order.price else fill_price) * order.quantity * Decimal("1000")
                PortfolioRepository.unblock_cash(db, portfolio, blocked_amount)
                print(f"✅ Unblocked {blocked_amount} VNĐ for order {order.id} (price used: {order.price if order.price else fill_price})")
            
            # Trừ tiền thực tế
            # Trong PRACTICE mode, cho phép balance âm (số dư ảo)
            # Trong REALTIME mode, đã validate ở validate_order rồi
            PortfolioRepository.update_cash_balance(db, portfolio, -total_cost)
            
            # Thêm position (CHỈ khi FILLED)
            VirtualPositionRepository.create_or_update_position(
                db, order.user_id, order.symbol, order.quantity, fill_price
            )
        else:  # SELL
            # Cộng tiền, trừ position
            # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
            total_revenue = fill_price * order.quantity * Decimal("1000")
            PortfolioRepository.update_cash_balance(db, portfolio, total_revenue)
            VirtualPositionRepository.create_or_update_position(
                db, order.user_id, order.symbol, -order.quantity, fill_price
            )
        
        # Update portfolio total value
        TradingService.update_portfolio_value(db, order.user_id, ch_client=None)
        
        return order, None
    
    @staticmethod
    def cancel_order(
        db: Session,
        user_id: int,
        order_id: int
    ) -> Tuple[Optional[VirtualOrder], Optional[str]]:
        """
        Cancel order
        Returns: (order, error_message)
        """
        order = VirtualOrderRepository.get_by_id(db, order_id)
        if not order:
            return None, "Order not found"
        
        if order.user_id != user_id:
            return None, "Unauthorized"
        
        if order.status not in ["PENDING", "QUEUED"]:
            return None, f"Cannot cancel {order.status} order"
        
        # Unblock tiền nếu là BUY order đã bị block (chỉ REALTIME mode)
        if order.side == "BUY" and order.trading_mode == "REALTIME":
            portfolio = PortfolioRepository.get_or_create_portfolio(db, user_id)
            # Tính blocked amount (có thể là price ban đầu nếu là LIMIT order)
            # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính tiền
            blocked_amount = (order.price if order.price else Decimal("0")) * order.quantity * Decimal("1000")
            if blocked_amount > 0:
                PortfolioRepository.unblock_cash(db, portfolio, blocked_amount)
                print(f"✅ Unblocked {blocked_amount} VNĐ for cancelled order {order.id}")
        
        order = VirtualOrderRepository.cancel_order(db, order)
        return order, None
    
    @staticmethod
    def update_portfolio_value(
        db: Session,
        user_id: int,
        ch_client = None,
        as_of_date: Optional[datetime] = None,
        update_db: bool = True
    ) -> Optional[Decimal]:
        """
        Cập nhật total value của portfolio dựa trên positions và cash
        
        Args:
            db: Database session
            user_id: User ID
            ch_client: ClickHouse client (None nếu không có giá real-time)
            as_of_date: Thời điểm tính toán (None = real-time, có giá trị = simulation)
            update_db: Có cập nhật vào database không (False cho simulation)
        
        Returns: total_value
        """
        portfolio = PortfolioRepository.get_by_user_id(db, user_id)
        if not portfolio:
            return None
        
        positions = VirtualPositionRepository.get_all_by_user(db, user_id)
        total_positions_value = Decimal("0")
        total_unrealized_pnl = Decimal("0")
        
        # Tính giá trị positions
        for position in positions:
            if ch_client:
                # Lấy giá từ ClickHouse (real-time hoặc tại thời điểm cụ thể)
                current_price = TradingService.get_current_price(ch_client, position.symbol, as_of_date)
                if current_price:
                    if update_db:
                        # Cập nhật vào database
                        position = VirtualPositionRepository.update_position_price(
                            db, position, current_price
                        )
                    else:
                        # Chỉ tính toán, không update DB (simulation mode)
                        # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính P&L
                        unrealized_pnl = (current_price - position.avg_price) * position.quantity * Decimal("1000")
                        total_unrealized_pnl += unrealized_pnl
                    
                    # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính giá trị position
                    total_positions_value += current_price * position.quantity * Decimal("1000")
                else:
                    # Fallback: dùng last_price hoặc avg_price
                    # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính giá trị position
                    price = position.last_price or position.avg_price
                    total_positions_value += price * position.quantity * Decimal("1000")
            else:
                # Dùng last_price hoặc avg_price
                # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính giá trị position
                price = position.last_price or position.avg_price
                total_positions_value += price * position.quantity * Decimal("1000")
        
        total_value = portfolio.cash_balance + total_positions_value
        
        if update_db:
            PortfolioRepository.update_total_value(db, portfolio, total_value)
        
        # Return dict với thông tin chi tiết (để có thể extend sau)
        return {
            "total_value": total_value,
            "cash_balance": portfolio.cash_balance,
            "total_positions_value": total_positions_value,
            "total_unrealized_pnl": total_unrealized_pnl
        }
    
    @staticmethod
    def check_and_fill_queued_market_orders(
        db: Session,
        user_id: Optional[int] = None,
        ch_client = None
    ) -> Dict:
        """
        Kiểm tra và fill các QUEUED MARKET orders khi vào giờ giao dịch
        
        Lưu ý: Chỉ fill khi đang trong giờ giao dịch (9:00-11:30, 13:00-15:00, Thứ 2-6)
        vì ngoài giờ giao dịch không có giá real-time.
        
        Args:
            db: Database session
            user_id: User ID (None = check tất cả users)
            ch_client: ClickHouse client
        
        Returns:
            Dict với thông tin về số orders đã fill
        """
        if not ch_client:
            return {"filled": 0, "checked": 0, "errors": []}
        
        # Kiểm tra xem có đang trong giờ giao dịch không
        # Ngoài giờ giao dịch không có giá real-time, nên không thể fill
        can_trade, trade_error = TradingHoursService.can_trade_now("REALTIME")
        if not can_trade:
            return {
                "filled": 0, 
                "checked": 0, 
                "errors": [], 
                "message": f"Ngoài giờ giao dịch. {trade_error}",
                "can_trade": False
            }
        
        # Lấy tất cả QUEUED MARKET orders
        queued_orders = VirtualOrderRepository.get_queued_market_orders(db, user_id=user_id)
        
        filled_count = 0
        checked_count = len(queued_orders)
        errors = []
        
        for order in queued_orders:
            try:
                # Lấy giá hiện tại (chỉ có giá khi trong giờ giao dịch)
                current_price = TradingService.get_current_price(ch_client, order.symbol)
                
                if not current_price:
                    errors.append(f"Order {order.id}: Could not get price for {order.symbol} (có thể ngoài giờ giao dịch)")
                    continue
                
                # Fill order với giá hiện tại
                fill_result, fill_error = TradingService.fill_order(
                    db, order.id, current_price, ch_client
                )
                if fill_error:
                    errors.append(f"Order {order.id}: {fill_error}")
                else:
                    filled_count += 1
                    print(f"✅ Filled QUEUED order {order.id}: {order.symbol} {order.side} {order.quantity} @ {current_price}")
                    
            except Exception as e:
                errors.append(f"Order {order.id}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return {
            "filled": filled_count,
            "checked": checked_count,
            "errors": errors,
            "can_trade": True
        }
    
    @staticmethod
    def get_portfolio_summary(
        db: Session,
        user_id: int,
        ch_client = None
    ) -> Dict:
        """Lấy portfolio summary với positions"""
        # Tự động check và fill QUEUED MARKET orders nếu đang trong giờ giao dịch
        # (Ngoài giờ giao dịch không có giá real-time, nên không fill được)
        if ch_client:
            TradingService.check_and_fill_queued_market_orders(db, user_id=user_id, ch_client=ch_client)
            # Tự động check và fill LIMIT orders khi giá đạt mức giới hạn
            TradingService.check_and_fill_limit_orders(db, user_id=user_id, ch_client=ch_client)
        
        portfolio = PortfolioRepository.get_or_create_portfolio(db, user_id)
        positions = VirtualPositionRepository.get_all_by_user(db, user_id)
        
        # Update positions với giá real-time nếu có ch_client
        total_positions_value = Decimal("0")
        total_unrealized_pnl = Decimal("0")
        
        for position in positions:
            if ch_client:
                current_price = TradingService.get_current_price(ch_client, position.symbol)
                if current_price:
                    position = VirtualPositionRepository.update_position_price(
                        db, position, current_price
                    )
            
            # Giá từ ClickHouse là nghìn VNĐ, cần nhân 1000 khi tính giá trị position
            position_value = (position.last_price or position.avg_price) * position.quantity * Decimal("1000")
            total_positions_value += position_value
            total_unrealized_pnl += position.unrealized_pnl
        
        return {
            "portfolio": portfolio,
            "positions": positions,
            "total_positions_value": total_positions_value,
            "total_unrealized_pnl": total_unrealized_pnl
        }
    
    @staticmethod
    def check_and_fill_limit_orders(
        db: Session,
        user_id: Optional[int] = None,
        ch_client = None,
        as_of_date: Optional[datetime] = None
    ) -> Dict:
        """
        Kiểm tra và fill các LIMIT orders khi giá đạt mức giới hạn
        
        Args:
            db: Database session
            user_id: User ID (None = check tất cả users)
            ch_client: ClickHouse client
            as_of_date: Thời điểm check (None = real-time, có giá trị = simulation)
        
        Returns:
            Dict với thông tin về số orders đã fill
        """
        if not ch_client:
            return {"filled": 0, "checked": 0, "errors": []}
        
        # Lấy tất cả LIMIT orders đang pending/queued
        pending_orders = VirtualOrderRepository.get_pending_limit_orders(db, user_id=user_id)
        
        filled_count = 0
        checked_count = len(pending_orders)
        errors = []
        
        for order in pending_orders:
            try:
                # Xác định thời điểm lấy giá
                price_time = order.execution_time if order.execution_time else as_of_date
                
                # Lấy giá hiện tại hoặc tại thời điểm cụ thể
                current_price = TradingService.get_current_price(
                    ch_client, order.symbol, as_of_date=price_time
                )
                
                if not current_price:
                    errors.append(f"Order {order.id}: Could not get price for {order.symbol}")
                    continue
                
                # Kiểm tra điều kiện fill
                should_fill = False
                reason = ""
                
                if order.side == "BUY":
                    # BUY LIMIT: fill khi giá hiện tại <= giá giới hạn
                    if current_price <= order.price:
                        should_fill = True
                        reason = f"Price {current_price} <= limit {order.price}"
                    else:
                        reason = f"Price {current_price} > limit {order.price} (chưa đạt)"
                else:  # SELL
                    # SELL LIMIT: fill khi giá hiện tại >= giá giới hạn
                    if current_price >= order.price:
                        should_fill = True
                        reason = f"Price {current_price} >= limit {order.price}"
                    else:
                        reason = f"Price {current_price} < limit {order.price} (chưa đạt)"
                
                if should_fill:
                    # Fill order với giá giới hạn (limit price)
                    fill_result, fill_error = TradingService.fill_order(
                        db, order.id, order.price, ch_client
                    )
                    if fill_error:
                        errors.append(f"Order {order.id}: {fill_error}")
                    else:
                        filled_count += 1
                else:
                    # Log lý do chưa fill (để debug)
                    errors.append(f"Order {order.id} ({order.side} {order.symbol}): {reason}")
                        
            except Exception as e:
                errors.append(f"Order {order.id}: {str(e)}")
        
        return {
            "filled": filled_count,
            "checked": checked_count,
            "errors": errors,
            "details": {
                "filled_count": filled_count,
                "not_filled_count": checked_count - filled_count
            }
        }

