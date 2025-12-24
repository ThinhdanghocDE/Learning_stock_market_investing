import asyncio
import websockets
import json
from datetime import datetime, timezone, timedelta
from clickhouse_driver import Client as CHClient
import os
from dotenv import load_dotenv

load_dotenv()

# ClickHouse connection
CH_CLIENT = CHClient(
    host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
    port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
    user=os.getenv('CLICKHOUSE_USER', 'default'),
    password=os.getenv('CLICKHOUSE_PASSWORD', ''),
    database=os.getenv('CLICKHOUSE_DB', 'stock_db')
)

connected_clients = {}  # {websocket: [symbols]}

async def register_client(websocket):
    connected_clients[websocket] = []
    print(f"✅ Client connected. Total: {len(connected_clients)}")

async def unregister_client(websocket):
    if websocket in connected_clients:
        del connected_clients[websocket]
    print(f"❌ Client disconnected. Total: {len(connected_clients)}")
def is_valid_candle(candle, last_close):
    if last_close == 0: return True
    
    # Nếu giá biến động > 20% trong 1 phút, khả năng cao là dữ liệu nhiễu
    change = abs(candle['close'] - last_close) / last_close
    if change > 0.20:
        print(f"⚠️ Phát hiện dữ liệu nhiễu cho {candle['symbol']}: {candle['close']} (lệch {change*100:.2f}%)")
        return False
    return True

# Lưu trữ giá đóng cửa gần nhất của các mã để so sánh
last_prices = {}
async def send_historical_data(websocket, symbol, limit=2000):
    try:
        # Lấy 60 nến mới nhất dựa trên ORDER BY và LIMIT
        query = """
        SELECT 
            symbol, time, argMinMerge(open), maxMerge(high), 
            minMerge(low), argMaxMerge(close), sumMerge(volume), 
            sumMerge(total_gross_trade_amount)
        FROM stock_db.ohlc
        WHERE symbol = %(symbol)s AND interval = '1m'
        GROUP BY symbol, time 
        ORDER BY time DESC 
        LIMIT %(limit)s
        """
        rows = CH_CLIENT.execute(query, {'symbol': symbol, 'limit': limit})
        
        # Chuyển đổi dữ liệu và ĐẢO NGƯỢC mảng (vì lấy DESC thì nến mới nhất ở đầu)
        candles = []
        for row in rows:
            vol = float(row[6]) if row[6] else 0
            vwap = float(row[7]) / vol if vol > 0 else 0
            
            # Xử lý timezone (giữ nguyên logic convert về UTC timestamp của bạn)
            dt = row[1]
            vn_tz = timezone(timedelta(hours=7))
            if dt.tzinfo is None:
                dt_utc = dt.replace(tzinfo=vn_tz).astimezone(timezone.utc)
                timestamp = int(dt_utc.timestamp())
            else:
                timestamp = int(dt.timestamp())

            candles.append({
                "time": timestamp,
                "open": float(row[2]), "high": float(row[3]),
                "low": float(row[4]), "close": float(row[5]),
                "volume": int(vol), "vwap": vwap
            })
        
        # Đảo ngược để nến cũ ở trước, nến mới ở sau cho biểu đồ vẽ đúng
        candles.reverse() 
        
        await websocket.send(json.dumps({"type": "historical", "symbol": symbol, "data": candles}))
    except Exception as e:
        print(f"❌ Error sending history: {e}")

# ============================================================
# ĐÂY LÀ HÀM BẠN ĐANG THIẾU
# ============================================================
async def handle_client(websocket):
    """Hàm xử lý logic cho từng client kết nối tới"""
    await register_client(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get('action')
                symbol = data.get('symbol', '').upper()

                if action == 'subscribe' and symbol:
                    connected_clients[websocket] = [symbol] 
    
                    print(f"📊 Client switched/subscribed to: {symbol}")
                    await send_historical_data(websocket, symbol)
                
                elif action == 'unsubscribe' and symbol:
                    if symbol in connected_clients[websocket]:
                        connected_clients[websocket].remove(symbol)
                        print(f"📉 Unsubscribed: {symbol}")

            except json.JSONDecodeError:
                pass 
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await unregister_client(websocket)

async def monitor_ohlc_updates():
    while True:
        try:
            all_subscribed_symbols = set()
            for subs in connected_clients.values():
                all_subscribed_symbols.update(subs)

            if not all_subscribed_symbols:
                await asyncio.sleep(1)
                continue

            query = """
            SELECT 
                symbol, time, argMinMerge(open), maxMerge(high), 
                minMerge(low), argMaxMerge(close), sumMerge(volume), 
                sumMerge(total_gross_trade_amount)
            FROM stock_db.ohlc
            WHERE interval = '1m' 
            AND symbol IN %(symbols)s
            AND time >= now() - INTERVAL 2 MINUTE 
            GROUP BY symbol, time 
            ORDER BY time DESC 
            LIMIT 1
            """
            
            rows = CH_CLIENT.execute(query, {'symbols': list(all_subscribed_symbols)})
            
            for row in rows:
                symbol = row[0]
                vol = float(row[6])
                raw_close = float(row[5])
                
                # Logic lọc nhiễu
                prev_price = last_prices.get(symbol, 0)
                if prev_price > 0:
                    # Nếu nến mới vọt lên quá cao (như giá 65 trong hình), ta bỏ qua không gửi
                    if abs(raw_close - prev_price) / prev_price > 0.15: # Ngưỡng 15%
                        continue 

                last_prices[symbol] = raw_close
                vwap = float(row[7]) / vol if vol > 0 else 0
                
                update_msg = json.dumps({
                    "type": "candle_update",
                    "symbol": symbol,
                    "data": {
                        "time": int(row[1].timestamp()),
                        "open": float(row[2]), "high": float(row[3]),
                        "low": float(row[4]), "close": raw_close,
                        "volume": int(vol), "vwap": vwap
                    }
                })

                for ws, subs in connected_clients.items():
                    if symbol in subs:
                        await ws.send(update_msg)
                        
        except Exception as e:
            print(f"❌ Monitor error: {e}")
        
        await asyncio.sleep(1)

async def main():
    monitor_task = asyncio.create_task(monitor_ohlc_updates())
    host = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
    port = int(os.getenv('WEBSOCKET_PORT', 8765))
    
    async with websockets.serve(handle_client, host, port):
        print(f"🚀 Server running on ws://{host}:{port}")
        await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✨ Server stopped")