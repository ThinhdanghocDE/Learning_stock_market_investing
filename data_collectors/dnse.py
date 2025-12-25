import json
import paho.mqtt.client as mqtt
from requests import post, get
from random import randint
import ssl
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
from clickhouse_driver import Client
from queue import Queue
import threading

# =====================
# LOAD ENV
# =====================
load_dotenv()

USERNAME = os.getenv("DNSE_USERNAME")
PASSWORD = os.getenv("DNSE_PASSWORD")

# ClickHouse connection
CH_CLIENT = Client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    database=os.getenv("CLICKHOUSE_DB", "stock_db"),
    user=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD", "")
)

# Batch insert queue
tick_queue = Queue()
BATCH_SIZE = 100  # Insert mỗi 100 ticks

# Danh sách mã cổ phiếu được phép lấy dữ liệu
ALLOWED_SYMBOLS = {
    'BSR', 'CEO', 'HPG', 'MBB', 'VPB', 'SHB', 'FPT', 'MSN', 'TCB', 'STB',
    'CTG', 'VNM', 'ACB', 'DGC', 'DBC', 'VCB', 'HDB', 'DCM', 'BID', 'CII',
    'EIB', 'BAF', 'GAS', 'LPB', 'CTD', 'CTS', 'AAA', 'ANV', 'CSV', 'DDV'
}

# Nhập thông tin vào đây (nếu có), và comment đoạn try...except bên dưới
investor_id = None
token = None

def authenticate(USERNAME, PASSWORD):
    try:
        url = "https://api.dnse.com.vn/user-service/api/auth"
        _json = {
            "username": USERNAME,
            "password": PASSWORD
        }
        response = post(url, json=_json)
        response.raise_for_status()

        print("Authentication successful!")
        return response.json().get("token")

    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def get_investor_info(token = None):
    try:
        url = f"https://api.dnse.com.vn/user-service/api/me"
        headers = {
            "authorization": f"Bearer {token}"
        }

        response = get(url, headers=headers)
        response.raise_for_status()
        investor_info = response.json()
        print("Get investor info successful!")
        return investor_info

    except Exception as e:
        print(f"Failed to get investor info: {e}")
        return None

try: # Có thể comment nếu có thông tin
    token = authenticate(USERNAME, PASSWORD)
    if token is not None:
        investor_info = get_investor_info(token=token)
        if investor_info is not None:
            investor_id = str(investor_info["investorId"])
        else:
            raise Exception("Failed to get investor info.")
    else:
        raise Exception("Authentication failed.")

except Exception as e:
    print(f"Error: {e}")
    exit()

# =====================
# HELPER FUNCTIONS
# =====================

def extract_market(market_id):
    """
    Extract market từ marketId
    
    Enum mapping theo DNSE documentation:
    - MARKET_ID_STO = 6 → STO = HoSE Stock Market → "HOSE"
    - MARKET_ID_STX = 7 → STX = HNX Listed Stock Market → "HNX"
    - MARKET_ID_UPX = 8 → UPX = HNX UpCoM Stock Market → "UPCOM"
    - MARKET_ID_BDO = 1 → BDO = HoSE Bond Market
    - MARKET_ID_BDX = 2 → BDX = HNX Government Bond Market
    - MARKET_ID_DVX = 3 → DVX = HNX Derivative Market
    - MARKET_ID_HCX = 4 → HCX = HNX Corporate Bond Market
    - MARKET_ID_RPO = 5 → RPO = HoSE Repo Market
    """
    if not market_id:
        return "HOSE"  # Default
    
    # Check enum value (số)
    if isinstance(market_id, (int, float)):
        if market_id == 6:
            return "HOSE"  # STO
        elif market_id == 7:
            return "HNX"  # STX
        elif market_id == 8:
            return "UPCOM"  # UPX
        elif market_id == 1:
            return "BDO"  # HoSE Bond
        elif market_id == 2:
            return "BDX"  # HNX Government Bond
        elif market_id == 3:
            return "DVX"  # HNX Derivative
        elif market_id == 4:
            return "HCX"  # HNX Corporate Bond
        elif market_id == 5:
            return "RPO"  # HoSE Repo
    
    # Check string
    market_id_upper = str(market_id).upper()
    if "STO" in market_id_upper or "HOSE" in market_id_upper:
        return "HOSE"
    elif "STX" in market_id_upper or "HNX" in market_id_upper:
        return "HNX"
    elif "UPX" in market_id_upper or "UPCOM" in market_id_upper:
        return "UPCOM"
    elif "BDO" in market_id_upper:
        return "BDO"
    elif "BDX" in market_id_upper:
        return "BDX"
    elif "DVX" in market_id_upper:
        return "DVX"
    elif "HCX" in market_id_upper:
        return "HCX"
    elif "RPO" in market_id_upper:
        return "RPO"
    
    return str(market_id).replace("MARKET_ID_", "")

def extract_board_id(board_id_str):
    """
    Extract board ID từ boardId
    
    Enum mapping theo DNSE documentation:
    - BOARD_ID_G1 = 2 → G1 (Lô chẵn, gộp G1, G7, G3)
    - BOARD_ID_G3 = 4 → G3 (Lô chẵn, gộp G1, G7, G3)
    - BOARD_ID_G7 = 6 → G7 (Lô chẵn, gộp G1, G7, G3)
    - BOARD_ID_G4 = 5 → G4 (Lô lẻ)
    - BOARD_ID_T1 = 9 → T1 (Thoả thuận lô chẵn, gộp T1, T2, T3)
    - BOARD_ID_T2 = 10 → T2
    - BOARD_ID_T3 = 11 → T3
    - BOARD_ID_T4 = 12 → T4 (Thoả thuận lô lẻ, gộp T4, T6)
    - BOARD_ID_T6 = 13 → T6
    """
    if not board_id_str:
        return "G1"  # Default
    
    # Check enum value (số)
    if isinstance(board_id_str, (int, float)):
        if board_id_str == 2:
            return "G1"
        elif board_id_str == 4:
            return "G3"
        elif board_id_str == 6:
            return "G7"
        elif board_id_str == 5:
            return "G4"
        elif board_id_str == 9:
            return "T1"
        elif board_id_str == 10:
            return "T2"
        elif board_id_str == 11:
            return "T3"
        elif board_id_str == 12:
            return "T4"
        elif board_id_str == 13:
            return "T6"
    
    # Check string
    board_id_upper = str(board_id_str).upper()
    if "G1" in board_id_upper:
        return "G1"
    elif "G3" in board_id_upper:
        return "G3"
    elif "G7" in board_id_upper:
        return "G7"
    elif "G4" in board_id_upper:
        return "G4"
    elif "T1" in board_id_upper:
        return "T1"
    elif "T2" in board_id_upper:
        return "T2"
    elif "T3" in board_id_upper:
        return "T3"
    elif "T4" in board_id_upper:
        return "T4"
    elif "T6" in board_id_upper:
        return "T6"
    
    return str(board_id_str).replace("BOARD_ID_", "")

def extract_session(session_id_raw):
    try:
        # Chuyển đổi về int để so sánh chính xác với Enum trong tài liệu
        sid = int(session_id_raw)
        
        if sid == 2: # TRADING_SESSION_ID_10
            return "ATO"
        elif sid == 6: # TRADING_SESSION_ID_30
            return "ATC"
        elif sid == 7: # TRADING_SESSION_ID_40
            return "CONTINUOUS"
        
        # Các phiên khác nếu cần xử lý thêm (ví dụ: nghỉ trưa, đóng cửa)
        elif sid == 9: # TRADING_SESSION_ID_99
            return "CLOSED"
            
        return "OTHERS"
    except (ValueError, TypeError):
        # Fallback xử lý nếu session_id là chuỗi (ATO, ATC...)
        s_str = str(session_id_raw).upper()
        if "ATO" in s_str or "10" in s_str: return "ATO"
        if "ATC" in s_str or "30" in s_str: return "ATC"
        if "CONTINUOUS" in s_str or "40" in s_str: return "CONTINUOUS"
        return "OTHERS"

def extract_side(side_str):
    """
    Extract side từ side
    
    Enum mapping theo DNSE documentation:
    - SIDE_BUY = 1 → BUY
    - SIDE_SELL = 2 → SELL
    """
    if not side_str:
        return "BUY"  # Default
    
    # Check enum value (số)
    if isinstance(side_str, (int, float)):
        if side_str == 1:
            return "BUY"
        elif side_str == 2:
            return "SELL"
    
    # Check string
    side_upper = str(side_str).upper()
    if "SELL" in side_upper or side_upper == "2":
        return "SELL"
    elif "BUY" in side_upper or side_upper == "1":
        return "BUY"
    
    return str(side_str).replace("SIDE_", "")

def parse_dnse_tick(payload):
    """
    Parse và normalize dữ liệu từ DNSE MQTT theo tài liệu kỹ thuật mới nhất.
    """
    try:
        # 1. Parse timestamp và xử lý Timezone VN
        sending_time_str = payload.get("sendingTime", "")
        if not sending_time_str:
            return None
        
        # Tốc độ xử lý ISO format nhanh hơn khi replace Z
        dt_utc = datetime.fromisoformat(sending_time_str.replace('Z', '+00:00'))
        vn_timezone = timezone(timedelta(hours=7))
        timestamp_dt = dt_utc.astimezone(vn_timezone).replace(tzinfo=None)

        # 2. Extract các trường định danh
        symbol = payload.get("symbol", "")
        if not symbol: return None
        
        market = extract_market(payload.get("marketId"))
        board_id = extract_board_id(payload.get("boardId"))
        
        # 3. CHỈNH SỬA LOGIC PHIÊN (TradingSessionID)
        # Theo tài liệu: 2=ATO (10), 6=ATC (30), 7=CONTINUOUS (40)
        session_id_raw = payload.get("tradingSessionId")
        session = extract_session(session_id_raw)

        # 4. CHỈNH SỬA CHO REAL-TIME CHART
        # Gom nến đấu giá về khung giờ chuẩn để tránh nến bị "rác" trên biểu đồ
        if session == "ATO":
            # Gom mọi lệnh ATO vào nến 09:15:00
            timestamp_dt = timestamp_dt.replace(hour=9, minute=15, second=0, microsecond=0)
        elif session == "ATC":
            # Gom mọi lệnh ATC vào nến 14:45:00
            timestamp_dt = timestamp_dt.replace(hour=14, minute=45, second=0, microsecond=0)

        # 5. GIẢI QUYẾT VẤN ĐỀ VWAP
        # Thay vì dùng grossTradeAmount từ payload (có thể bị sai hoặc trễ), 
        # hãy tự tính toán giá trị khớp lệnh thực tế
        price = float(payload.get("matchPrice", 0))
        quantity = int(float(payload.get("matchQtty", 0)))
        
        # ClickHouse sẽ dùng cột này để tính VWAP = sum(gross_trade_amount) / sum(quantity)
        calculated_gross_amount = price * quantity 

        return {
            "symbol": symbol,
            "market": market,
            "timestamp": timestamp_dt,
            "price": price,
            "quantity": quantity,
            "side": extract_side(payload.get("side")),
            "session": session,
            "board_id": board_id,
            "total_volume": int(float(payload.get("totalVolumeTraded", 0))),
            "gross_trade_amount": calculated_gross_amount, # Dùng giá trị tự tính chuẩn xác
            "isin": payload.get("isin", ""),
            "sending_time": timestamp_dt
        }
    except Exception as e:
        print(f" Error parsing tick: {e}")
        return None

def insert_batch_to_clickhouse(batch):
    """Insert batch ticks vào ClickHouse"""
    if not batch:
        return
    
    try:
        CH_CLIENT.execute(
            'INSERT INTO stock_db.ticks (symbol, market, timestamp, price, quantity, side, session, board_id, total_volume, gross_trade_amount, isin, sending_time) VALUES',
            [(t['symbol'], t['market'], t['timestamp'], t['price'], t['quantity'], 
              t['side'], t['session'], t['board_id'], t['total_volume'], 
              t['gross_trade_amount'], t['isin'], t['sending_time']) 
             for t in batch]
        )
        print(f" Inserted {len(batch)} ticks to ClickHouse")
    except Exception as e:
        print(f" Error inserting batch: {e}")
        import traceback
        traceback.print_exc()

def batch_insert_worker():
    """Background thread để batch insert vào ClickHouse"""
    batch = []
    
    while True:
        try:
            # Lấy tick từ queue (blocking với timeout)
            tick = tick_queue.get(timeout=1)
            if tick is None:  # Sentinel value để stop thread
                # Insert batch cuối cùng trước khi exit
                if batch:
                    insert_batch_to_clickhouse(batch)
                break
            
            batch.append(tick)
            
            # Khi đủ batch size, insert vào ClickHouse
            if len(batch) >= BATCH_SIZE:
                insert_batch_to_clickhouse(batch)
                batch = []
        except:
            # Nếu timeout hoặc có lỗi, insert batch hiện tại (nếu có)
            if batch:
                insert_batch_to_clickhouse(batch)
                batch = []

# Start batch insert worker thread
batch_thread = threading.Thread(target=batch_insert_worker, daemon=True)
batch_thread.start()
print(" Batch insert worker thread started")

# Configuration
BROKER_HOST = "datafeed-lts-krx.dnse.com.vn"
BROKER_PORT = 443
CLIENT_ID_PREFIX = "dnse-price-json-mqtt-ws-sub-"

# Generate random client ID
client_id = f"{CLIENT_ID_PREFIX}{randint(1000, 2000)}"

# Create client
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id,
    protocol=mqtt.MQTTv5,
    transport="websockets"
)

# Set credentials
client.username_pw_set(investor_id, token)

# SSL/TLS configuration (since it's wss://)
client.tls_set(cert_reqs=ssl.CERT_NONE) # Bỏ qua kiểm tra SSL
client.tls_insecure_set(True) # Cho phép kết nối với chứng chỉ self-signed
client.ws_set_options(path="/wss")
client.enable_logger()

# Connect callback
def on_connect(client, userdata, flags, rc, properties):
    if rc == 0 and client.is_connected():
        print(" Connected to MQTT Broker!")

        symbol_list = sorted(list(ALLOWED_SYMBOLS))
        print(f" Subscribing to {len(symbol_list)} symbols (fixed list)...")

        for symbol in symbol_list:
            topic = f"plaintext/quotes/krx/mdds/tick/v1/roundlot/symbol/{symbol}"
            result, mid = client.subscribe(topic, qos=1)
            if result == 0:
                print(f"    Subscribed to {symbol}")
            else:
                print(f"    Failed to subscribe to {symbol}: {result}")

        print(" Subscription completed.")
    else:
        print(f" Failed to connect, return code {rc}")


# Message callback
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # ===== FILTER =====
        # Filter theo board_id và session_id (nếu là số)
        board_id_raw = payload.get("boardId")
        session_id_raw = payload.get("tradingSessionId")
        
        # Nếu board_id là số, check giá trị
        if isinstance(board_id_raw, (int, float)):
            if board_id_raw not in (2, 4, 6):  # G1, G3, G7
                return
        # Nếu là string, check trong string
        elif isinstance(board_id_raw, str):
            if "G1" not in board_id_raw and "G3" not in board_id_raw and "G7" not in board_id_raw:
                return
        
        # Nếu session_id là số, check giá trị
        # Enum mapping (theo DNSE documentation):
        # - TRADING_SESSION_ID_10 = 2 → 10 = ATO (Opening Call Auction)
        # - TRADING_SESSION_ID_30 = 6 → 30 = ATC (Closing Call Auction)
        # - TRADING_SESSION_ID_40 = 7 → 40 = CONTINUOUS (Continuous Auction)
        if isinstance(session_id_raw, (int, float)):
            if session_id_raw not in (2, 6, 7):  #  Enum values: 2=ATO, 6=ATC, 7=CONTINUOUS
                return
        # Nếu là string, check trong string
        elif isinstance(session_id_raw, str):
            if "10" not in session_id_raw and "30" not in session_id_raw and "40" not in session_id_raw:
                if "ATO" not in session_id_raw and "CONTINUOUS" not in session_id_raw and "ATC" not in session_id_raw:
                    return

        # ===== PARSE & NORMALIZE =====
        tick = parse_dnse_tick(payload)
        
        if tick is None:
            return
        
        # Print tick info (optional, có thể comment để giảm log)
        print(f" {tick['symbol']} | {tick['price']} | {tick['quantity']} | {tick['side']} | {tick['session']}")
        
        # Add to queue for batch insert
        tick_queue.put(tick)

    except Exception as e:
        print(f" Parse error: {e}")
        import traceback
        traceback.print_exc()

# Assign callback
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
client.connect(BROKER_HOST, BROKER_PORT, keepalive=1200)

# Start the network loop
client.loop_start()

# To keep the connection alive (or use loop_forever() instead of loop_start())
try:
    while True:
        pass
except KeyboardInterrupt:
    print("\n Disconnecting...")
    # Stop batch worker
    tick_queue.put(None)  # Sentinel value
    batch_thread.join(timeout=5)
    # Disconnect MQTT
    client.disconnect()
    client.loop_stop()
    print(" Disconnected successfully")
