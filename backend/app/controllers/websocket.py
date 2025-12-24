"""
WebSocket Controllers - Real-time OHLC Updates
"""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_clickhouse, get_db
from app.repositories.clickhouse_repository import ClickHouseRepository
from app.services.auth_service import AuthService
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# Store active WebSocket connections
class ConnectionManager:
    """Quản lý WebSocket connections"""
    
    def __init__(self):
        # {symbol: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # {websocket: user_id}
        self.websocket_users: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, symbol: str, user_id: int = None):
        """Kết nối WebSocket và subscribe vào symbol"""
        await websocket.accept()
        
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        
        self.active_connections[symbol].add(websocket)
        if user_id:
            self.websocket_users[websocket] = user_id
        
        logger.info(f"WebSocket connected: symbol={symbol}, user_id={user_id}, total={len(self.active_connections[symbol])}")
    
    def disconnect(self, websocket: WebSocket, symbol: str):
        """Ngắt kết nối WebSocket"""
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            if len(self.active_connections[symbol]) == 0:
                del self.active_connections[symbol]
        
        if websocket in self.websocket_users:
            del self.websocket_users[websocket]
        
        logger.info(f"WebSocket disconnected: symbol={symbol}")
    
    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """Gửi message đến tất cả clients đang subscribe symbol"""
        if symbol not in self.active_connections:
            return
        
        disconnected = set()
        for websocket in self.active_connections[symbol]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected connections
        for ws in disconnected:
            self.disconnect(ws, symbol)

# Global connection manager
manager = ConnectionManager()

# Store last candle data để detect updates (cả timestamp và hash của data)
last_candle_data: Dict[str, Dict] = {}  # {symbol: {"time": datetime, "hash": str}}

# Background task để monitor và push updates
async def monitor_ohlc_updates(ch_client, symbols: Set[str], interval_seconds: int = 5):
    """
    Background task để monitor OHLC updates và push qua WebSocket
    
    Logic:
    - Detect candle mới (timestamp mới)
    - Detect update trong cùng phút (timestamp giống nhưng data thay đổi)
    
    Args:
        ch_client: ClickHouse client
        symbols: Set các symbols cần monitor
        interval_seconds: Khoảng thời gian check (giây)
    """
    if not symbols:
        return
    
    repo = ClickHouseRepository(ch_client)
    
    try:
        for symbol in symbols:
            try:
                # Lấy OHLC mới nhất
                latest_data = repo.get_latest_ohlc(symbol, interval="1m", limit=1)
                
                if latest_data and len(latest_data) > 0:
                    latest_candle = latest_data[0]
                    candle_time = latest_candle["time"]
                    
                    # Tạo hash của candle data để detect update trong cùng phút
                    import hashlib
                    candle_hash = hashlib.md5(
                        f"{latest_candle.get('open')}_{latest_candle.get('high')}_{latest_candle.get('low')}_{latest_candle.get('close')}_{latest_candle.get('volume')}".encode()
                    ).hexdigest()
                    
                    # Parse candle_time để so sánh
                    if isinstance(candle_time, str):
                        try:
                            # Thử parse ISO format trước
                            if 'T' in candle_time:
                                candle_datetime = datetime.fromisoformat(candle_time.replace('Z', '+00:00'))
                            else:
                                candle_datetime = datetime.strptime(candle_time, '%Y-%m-%d %H:%M:%S')
                        except Exception as parse_error:
                            logger.warning(f"Error parsing candle_time {candle_time}: {parse_error}")
                            # Nếu parse fail, skip candle này
                            continue
                    else:
                        candle_datetime = candle_time
                    
                    # Đảm bảo datetime là naive (không có timezone) để so sánh dễ dàng
                    if candle_datetime.tzinfo is not None:
                        candle_datetime = candle_datetime.replace(tzinfo=None)
                    
                    # Kiểm tra xem có update không:
                    # 1. Candle mới (timestamp mới)
                    # 2. Cùng timestamp nhưng data thay đổi (update trong cùng phút)
                    should_push = False
                    
                    if symbol not in last_candle_data:
                        # Lần đầu tiên, luôn push
                        should_push = True
                    else:
                        last_data = last_candle_data[symbol]
                        last_time = last_data.get("time")
                        last_hash = last_data.get("hash")
                        
                        # Candle mới (timestamp mới)
                        if candle_datetime > last_time:
                            should_push = True
                        # Cùng timestamp nhưng data thay đổi (update trong cùng phút)
                        elif candle_datetime == last_time and candle_hash != last_hash:
                            should_push = True
                    
                    if should_push:
                        # Cập nhật last_candle_data
                        last_candle_data[symbol] = {
                            "time": candle_datetime,
                            "hash": candle_hash
                        }
                        
                        # Push update đến tất cả clients subscribe symbol này
                        await manager.broadcast_to_symbol(symbol, {
                            "type": "ohlc_update",
                            "symbol": symbol,
                            "data": latest_candle,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        logger.debug(f"Pushed OHLC update: {symbol} at {candle_time} (hash: {candle_hash[:8]})")
            
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
    
    except Exception as e:
        logger.error(f"Error in monitor_ohlc_updates: {e}")


async def authenticate_websocket(websocket: WebSocket, token: str = None) -> int:
    """
    Authenticate WebSocket connection
    
    Returns:
        user_id hoặc None nếu không authenticate
    """
    if not token:
        return None
    
    try:
        # Verify token (chỉ nhận token, không nhận db)
        token_data = AuthService.verify_token(token)
        if not token_data:
            return None
        
        # Lấy user từ database
        from app.database import SessionLocal
        from app.repositories.user_repository import UserRepository
        db = SessionLocal()
        try:
            user = UserRepository.get_by_username(db, username=token_data.username)
            if user:
                return user.id
        finally:
            db.close()
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
    
    return None


@router.websocket("/ws/ohlc/{symbol}")
async def websocket_ohlc(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(None, description="JWT token (optional, for authenticated users)"),
    interval: str = Query("1m", description="Interval: 1m, 5m, 1h, 1d")
):
    """
    WebSocket endpoint để nhận real-time OHLC updates cho một symbol
    
    - Kết nối: ws://localhost:8000/ws/ohlc/ACB?token=<jwt_token>&interval=1m
    - Nhận updates mỗi khi có candle mới
    - Message format: {"type": "ohlc_update", "symbol": "ACB", "data": {...}, "timestamp": "..."}
    """
    user_id = None
    if token:
        user_id = await authenticate_websocket(websocket, token)
        if user_id:
            logger.info(f"Authenticated WebSocket connection: user_id={user_id}, symbol={symbol}")
    
    # Kết nối
    await manager.connect(websocket, symbol, user_id)
    
    try:
        # Gửi welcome message
        await websocket.send_json({
            "type": "connected",
            "symbol": symbol,
            "interval": interval,
            "message": f"Connected to {symbol} OHLC stream"
        })
        
        # Background monitoring task đã được start trong lifespan
        # Chỉ cần keep connection alive và listen for messages
        while True:
            try:
                # Nhận message từ client (ping/pong hoặc commands)
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, symbol)


@router.websocket("/ws/ohlc")
async def websocket_ohlc_multiple(
    websocket: WebSocket,
    symbols: str = Query(..., description="Comma-separated symbols: ACB,VCB,VIC"),
    token: str = Query(None, description="JWT token (optional)")
):
    """
    WebSocket endpoint để nhận real-time OHLC updates cho nhiều symbols
    
    - Kết nối: ws://localhost:8000/ws/ohlc?symbols=ACB,VCB,VIC&token=<jwt_token>
    - Subscribe vào nhiều symbols cùng lúc
    """
    user_id = None
    if token:
        user_id = await authenticate_websocket(websocket, token)
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    # Kết nối với tất cả symbols
    for symbol in symbol_list:
        await manager.connect(websocket, symbol, user_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "symbols": symbol_list,
            "message": f"Connected to {len(symbol_list)} symbols"
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            except WebSocketDisconnect:
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Disconnect từ tất cả symbols
        for symbol in symbol_list:
            manager.disconnect(websocket, symbol)


# Background task để start monitoring (sẽ được start trong main.py)
async def start_ohlc_monitoring(ch_client, interval_seconds: int = 5):
    """
    Start background task để monitor OHLC updates cho tất cả active symbols
    """
    while True:
        try:
            # Lấy tất cả symbols đang có connections
            active_symbols = set(manager.active_connections.keys())
            
            if active_symbols:
                # Monitor và push updates
                await monitor_ohlc_updates(ch_client, active_symbols, interval_seconds)
            
            # Sleep trước khi check lại
            await asyncio.sleep(interval_seconds)
        
        except asyncio.CancelledError:
            logger.info("OHLC monitoring task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in start_ohlc_monitoring: {e}")
            await asyncio.sleep(interval_seconds)

