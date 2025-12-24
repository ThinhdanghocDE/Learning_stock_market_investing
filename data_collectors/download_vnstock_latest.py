"""
Script để lấy dữ liệu mới nhất từ vnstock (bao gồm cả intraday real-time)
Giải quyết vấn đề chỉ lấy được data đến ngày 14
"""

import os
import sys
from datetime import datetime, timedelta, timezone
import time
import pandas as pd
from dotenv import load_dotenv
from clickhouse_driver import Client as CHClient

load_dotenv()

# ClickHouse connection
CH_CLIENT = CHClient(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    database=os.getenv("CLICKHOUSE_DB", "stock_db"),
    user=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD", "")
)

def check_vnstock_installed():
    """Kiểm tra xem vnstock đã được cài đặt chưa"""
    try:
        from vnstock import Quote
        return True
    except ImportError:
        print(" vnstock chua duoc cai dat!")
        print("\nCai dat vnstock:")
        print("  pip install vnstock")
        return False

def get_latest_data_vnstock(symbol):
    """
    Lấy dữ liệu mới nhất từ vnstock (bao gồm cả intraday)
    
    Args:
        symbol: Mã cổ phiếu (ví dụ: 'VIC', 'VNM', 'VCB')
    """
    try:
        from vnstock import Quote
        
        print(f"\nDang lay du lieu moi nhat cho {symbol}...")
        
        # Khởi tạo Quote object
        quote = Quote(symbol=symbol, source='VCI')
        
        # 1. Thử lấy intraday data trước (real-time, mới nhất)
        print("  1. Thu lay intraday data (real-time)...")
        try:
            df_intraday = quote.intraday(symbol=symbol, page_size=10000, show_log=False)
            if df_intraday is not None and not df_intraday.empty:
                print(f"      Lay duoc {len(df_intraday)} records tu intraday")
                print(f"     Latest time: {df_intraday.index[-1] if isinstance(df_intraday.index, pd.DatetimeIndex) else 'N/A'}")
        except Exception as e:
            print(f"     WARNING: Khong the lay intraday: {e}")
            df_intraday = None
        
        # 2. Lấy historical data cho ngày 22-12-2025
        print("  2. Thu lay historical data cho ngay 22-12-2025...")
        start_date = '2025-12-24'
        end_date = '2025-12-24'
        try:
            df_historical = quote.history(
                start=start_date,
                end=end_date,
                interval='1m'  # Dữ liệu theo phút trong ngày 22-12-2025
            )
            if df_historical is not None and not df_historical.empty:
                print(f"      Lay duoc {len(df_historical)} records tu historical")
                print(f"     Index type: {type(df_historical.index)}")
                print(f"     Columns: {list(df_historical.columns)}")
                
                # Kiểm tra xem có cột thời gian trong columns không
                # Nếu index là RangeIndex, tìm cột thời gian để làm index
                time_column = None
                if isinstance(df_historical.index, pd.RangeIndex):
                    # Tìm cột thời gian (time, date, datetime, timestamp)
                    for col in ['time', 'date', 'datetime', 'timestamp', 'Time', 'Date', 'DateTime']:
                        if col in df_historical.columns:
                            time_column = col
                            break
                    
                    if time_column:
                        print(f"     Found '{time_column}' column, using it as index...")
                        df_historical[time_column] = pd.to_datetime(df_historical[time_column], errors='coerce')
                        # Loại bỏ các dòng có time không hợp lệ
                        initial_count = len(df_historical)
                        df_historical = df_historical.dropna(subset=[time_column])
                        df_historical = df_historical.set_index(time_column)
                        print(f"      Set '{time_column}' column as index, {len(df_historical)} valid records")
                    else:
                        print(f"     WARNING: Warning: RangeIndex but no time column found in: {list(df_historical.columns)}")
                elif not isinstance(df_historical.index, pd.DatetimeIndex):
                    print(f"     Converting index to DatetimeIndex...")
                    df_historical.index = pd.to_datetime(df_historical.index, errors='coerce')
                    # Loại bỏ các dòng có timestamp không hợp lệ
                    initial_count = len(df_historical)
                    df_historical = df_historical.dropna(subset=[df_historical.columns[0]])
                    if len(df_historical) < initial_count:
                        print(f"     WARNING: Removed {initial_count - len(df_historical)} records with invalid timestamps")
                
                # Filter ra các records có năm 1970 (epoch 0) hoặc năm < 2000
                if isinstance(df_historical.index, pd.DatetimeIndex):
                    initial_count = len(df_historical)
                    df_historical = df_historical[df_historical.index.year >= 2000]
                    if len(df_historical) < initial_count:
                        print(f"     WARNING: Removed {initial_count - len(df_historical)} records with year < 2000")
                    print(f"     Time range: {df_historical.index[0]} to {df_historical.index[-1]}")
                else:
                    print(f"     WARNING: Warning: Index is still not DatetimeIndex after conversion")
                    print(f"     First index value: {df_historical.index[0]}")
                    print(f"     Last index value: {df_historical.index[-1]}")
        except Exception as e:
            print(f"     WARNING: Khong the lay historical: {e}")
            df_historical = None
        
        # 3. Kết hợp dữ liệu (ưu tiên historical ngày 22-12-2025, sau đó bổ sung intraday nếu có)
        if df_historical is not None and not df_historical.empty:
            df = df_historical
            print(f"   Su dung historical data ngay 22-12-2025 ({len(df)} records)")
            
            # Nếu có intraday data, kết hợp vào (bổ sung dữ liệu mới nhất)
            if df_intraday is not None and not df_intraday.empty:
                print(f"   Bo sung intraday data ({len(df_intraday)} records)...")
                # Có thể append intraday vào historical nếu cần
                # Tạm thời chỉ dùng historical để đảm bảo có đủ 1825 ngày
        elif df_intraday is not None and not df_intraday.empty:
            df = df_intraday
            print(f"  WARNING: Chi co intraday data ({len(df)} records), khong co historical")
        else:
            print(f"   Khong co du lieu nao")
            return None
        
        return df
        
    except Exception as e:
        print(f"   Loi khi lay du lieu: {e}")
        import traceback
        traceback.print_exc()
        return None

def calculate_total_gross_trade_amount(high, low, close, volume):
    """
    Tính total_gross_trade_amount theo công thức:
    Typical Price = (high + low + close) / 3
    total_gross_trade_amount = Typical Price × volume
    """
    typical_price = (high + low + close) / 3.0
    return typical_price * volume

def insert_vnstock_data_to_clickhouse(df, symbol):
    """
    Insert dữ liệu từ vnstock DataFrame vào ClickHouse bảng ohlc
    
    Args:
        df: DataFrame từ vnstock
        symbol: Mã cổ phiếu
    """
    if df is None or df.empty:
        return False
    
    try:
        print(f"\nDang insert {len(df)} records vao ClickHouse...")
        
        inserted = 0
        skipped = 0
        batch_data = []  # Batch insert để tăng performance
        
        # Kiểm tra xem là intraday data hay historical data
        # Intraday có columns: ['time', 'price', 'volume', 'match_type', 'id']
        # Historical có columns: ['open', 'high', 'low', 'close', 'volume'] với index là time
        is_intraday = 'price' in df.columns and 'time' in df.columns
        
        if is_intraday:
            print(f"   Detected: Intraday data format")
            print(f"     Columns: {list(df.columns)}")
            print(f"     Will aggregate by minute to get OHLC...")
            
            # Aggregate intraday data theo phút để có OHLC
            # Chuyển time column thành datetime nếu chưa
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], errors='coerce')
                # Loại bỏ các dòng có time không hợp lệ
                df = df.dropna(subset=['time'])
                df = df.set_index('time')
                # Đảm bảo index là DatetimeIndex
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index, errors='coerce')
                    df = df.dropna(subset=[df.columns[0]])
            
            # Aggregate theo phút
            df_agg = df.groupby(pd.Grouper(freq='1min')).agg({
                'price': ['first', 'max', 'min', 'last'],  # open, high, low, close
                'volume': 'sum'
            })
            
            # Flatten column names
            df_agg.columns = ['open', 'high', 'low', 'close', 'volume']
            df_agg = df_agg.dropna()  # Bỏ các phút không có data
            
            print(f"     Aggregated to {len(df_agg)} records (1-minute bars)")
            df = df_agg
        else:
            print(f"   Detected: Historical data format")
            print(f"     Columns: {list(df.columns)}")
            print(f"     Index type: {type(df.index)}")
            
            # Đảm bảo index là DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                print(f"     Converting index to DatetimeIndex...")
                try:
                    df.index = pd.to_datetime(df.index, errors='coerce')
                    # Loại bỏ các dòng có timestamp không hợp lệ (NaT)
                    initial_count = len(df)
                    df = df.dropna(subset=[df.columns[0]])  # Drop rows với NaT index
                    nat_removed = initial_count - len(df)
                    if nat_removed > 0:
                        print(f"     WARNING: Removed {nat_removed} records with NaT timestamps")
                    
                    # Filter ra các records có năm 1970 (epoch 0)
                    if isinstance(df.index, pd.DatetimeIndex):
                        before_epoch_filter = len(df)
                        df = df[df.index.year >= 2000]
                        epoch_removed = before_epoch_filter - len(df)
                        if epoch_removed > 0:
                            print(f"     WARNING: Removed {epoch_removed} records with year < 2000")
                    
                    print(f"      Converted to DatetimeIndex, {len(df)} valid records remaining")
                except Exception as e:
                    print(f"     WARNING: Error converting index: {e}")
            else:
                # Index đã là DatetimeIndex, nhưng vẫn cần filter năm 1970
                initial_count = len(df)
                df = df[df.index.year >= 2000]
                if len(df) < initial_count:
                    print(f"     WARNING: Removed {initial_count - len(df)} records with year < 2000")
        
        # Đảm bảo index là DatetimeIndex trước khi xử lý
        if not isinstance(df.index, pd.DatetimeIndex):
            print(f"  WARNING: Warning: Index is not DatetimeIndex, attempting conversion...")
            print(f"     Index type: {type(df.index)}")
            print(f"     Sample index values: {df.index[:3].tolist() if len(df) > 0 else 'N/A'}")
            df.index = pd.to_datetime(df.index, errors='coerce')
            # Đếm số NaT (Not a Time) sau khi convert
            nat_count = df.index.isna().sum()
            if nat_count > 0:
                print(f"     WARNING: Found {nat_count} invalid timestamps (NaT), removing...")
            df = df.dropna(subset=[df.columns[0]])
            print(f"      After conversion: {len(df)} valid records")
        
        # Filter ra các records có timestamp không hợp lệ (năm 1970 = epoch 0)
        if isinstance(df.index, pd.DatetimeIndex):
            initial_count = len(df)
            # Loại bỏ các records có năm < 2000 (bao gồm năm 1970)
            df = df[df.index.year >= 2000]
            removed_count = initial_count - len(df)
            if removed_count > 0:
                print(f"   Removed {removed_count} records with invalid timestamps (year < 2000)")
                print(f"     Remaining: {len(df)} valid records")
            
            # Kiểm tra xem có cột 'time' trong columns không (có thể conflict với index)
            if 'time' in df.columns:
                print(f"  WARNING: Warning: Found 'time' column in data, removing to avoid conflict with index")
                df = df.drop(columns=['time'])
        
        # Bây giờ df đã có format chuẩn: index là time, columns là open, high, low, close, volume
        for idx, row in df.iterrows():
            try:
                # Parse timestamp từ index (đã đảm bảo là DatetimeIndex)
                timestamp = idx
                
                # Kiểm tra nếu là NaT (Not a Time)
                if pd.isna(timestamp):
                    skipped += 1
                    continue
                
                # Convert sang datetime object
                if isinstance(timestamp, pd.Timestamp):
                    timestamp = timestamp.to_pydatetime()
                elif hasattr(timestamp, 'to_pydatetime'):
                    timestamp = timestamp.to_pydatetime()
                elif isinstance(timestamp, datetime):
                    pass  # Đã là datetime
                elif isinstance(timestamp, (int, float)):
                    # Nếu là số, có thể là Unix timestamp
                    # Kiểm tra số chữ số để xác định milliseconds hay seconds
                    if timestamp > 1e12:  # Milliseconds (13+ digits)
                        timestamp = datetime.fromtimestamp(timestamp / 1000)
                    elif timestamp > 1e9:  # Seconds (10 digits)
                        timestamp = datetime.fromtimestamp(timestamp)
                    else:
                        # Số quá nhỏ, có thể là lỗi
                        print(f"  WARNING: Invalid timestamp value: {timestamp}, using current time")
                        timestamp = datetime.now()
                elif isinstance(timestamp, str):
                    try:
                        timestamp = pd.to_datetime(timestamp).to_pydatetime()
                    except:
                        try:
                            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        except:
                            try:
                                timestamp = datetime.strptime(timestamp, "%Y-%m-%d")
                            except:
                                print(f"  WARNING: Cannot parse timestamp string: {timestamp}, using current time")
                                timestamp = datetime.now()
                else:
                    # Thử convert bằng pandas
                    try:
                        timestamp = pd.to_datetime(timestamp).to_pydatetime()
                    except:
                        print(f"  WARNING: Cannot convert timestamp: {type(timestamp)} = {timestamp}, using current time")
                        timestamp = datetime.now()
                
                # Validate timestamp (đã filter trước nhưng vẫn kiểm tra để an toàn)
                if timestamp.year < 2000:
                    # Không nên xảy ra vì đã filter trước, nhưng vẫn kiểm tra
                    skipped += 1
                    continue
                
                # Debug: In một vài timestamp đầu tiên để kiểm tra
                if inserted == 0 and skipped == 0:
                    print(f"  📅 Sample timestamp: {timestamp} (type: {type(timestamp)})")
                    print(f"  📅 Sample data: open={row.get('open', 'N/A')}, close={row.get('close', 'N/A')}")
                
                # Lấy giá trị OHLCV
                open_val = float(row.get('open', row.get('Open', 0)))
                high_val = float(row.get('high', row.get('High', 0)))
                low_val = float(row.get('low', row.get('Low', 0)))
                close_val = float(row.get('close', row.get('Close', 0)))
                volume_val = int(float(row.get('volume', row.get('Volume', 0))))
                
                # Kiểm tra giá trị hợp lệ
                if open_val == 0 and high_val == 0 and low_val == 0 and close_val == 0:
                    skipped += 1
                    continue
                
                # Tính total_gross_trade_amount theo công thức:
                # Typical Price = (high + low + close) / 3
                # total_gross_trade_amount = Typical Price × volume
                total_gross_trade_amount = calculate_total_gross_trade_amount(
                    high_val, low_val, close_val, volume_val
                )
                
                # Convert timestamp sang UTC+7 (giờ Việt Nam) - naive datetime
                # ClickHouse lưu datetime UTC+7 (naive)
                vn_timezone = timezone(timedelta(hours=7))
                if timestamp.tzinfo is None:
                    # Nếu là naive datetime, giả sử đã là UTC+7
                    timestamp_vn = timestamp
                else:
                    # Convert từ UTC sang UTC+7
                    timestamp_utc = timestamp.astimezone(timezone.utc)
                    timestamp_vn = timestamp_utc.astimezone(vn_timezone).replace(tzinfo=None)
                
                # Thêm vào batch
                batch_data.append((
                    symbol,
                    timestamp_vn,  # DateTime (UTC+7, naive)
                    '1m',  # interval
                    open_val,
                    high_val,
                    low_val,
                    close_val,
                    volume_val,
                    0,  # trade_count (không có từ vnstock)
                    total_gross_trade_amount
                ))
                
                inserted += 1
                
                # Batch insert mỗi 1000 records
                if len(batch_data) >= 1000:
                    insert_batch_to_clickhouse(batch_data)
                    batch_data = []
                
            except Exception as e:
                skipped += 1
                if inserted == 0 and skipped <= 3:  # In lỗi đầu tiên để debug
                    print(f"  WARNING: Error inserting row: {e}")
                    print(f"     Index: {idx}, Row: {dict(row) if hasattr(row, 'to_dict') else 'N/A'}")
                continue
        
        # Insert batch cuối cùng nếu còn
        if batch_data:
            insert_batch_to_clickhouse(batch_data)
        
        print(f"\n Inserted: {inserted} records")
        print(f"WARNING: Skipped: {skipped} records")
        
        return inserted > 0
        
    except Exception as e:
        print(f"\n Loi khi insert vao ClickHouse: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_table_schema(table_name):
    """
    Kiểm tra schema của bảng trong ClickHouse
    
    Returns:
        dict với keys: 'columns', 'engine', 'has_trade_count'
    """
    try:
        # Lấy thông tin về bảng
        result = CH_CLIENT.execute(f"DESCRIBE TABLE stock_db.{table_name}")
        columns = {row[0]: row[1] for row in result}  # column_name: column_type
        
        # Kiểm tra engine
        engine_result = CH_CLIENT.execute(f"SELECT engine FROM system.tables WHERE database = 'stock_db' AND name = '{table_name}'")
        engine = engine_result[0][0] if engine_result else 'Unknown'
        
        return {
            'columns': columns,
            'engine': engine,
            'has_trade_count': 'trade_count' in columns
        }
    except Exception as e:
        print(f"  WARNING: Cannot check schema for {table_name}: {e}")
        return None

def create_temp_table_if_not_exists():
    """
    Tạo bảng tạm để insert OHLC data từ vnstock
    Bảng này dùng MergeTree (không phải AggregatingMergeTree) để có thể insert trực tiếp
    """
    try:
        # Kiểm tra xem bảng đã tồn tại chưa
        result = CH_CLIENT.execute(
            "SELECT name FROM system.tables WHERE database = 'stock_db' AND name = 'ohlc_vnstock_temp'"
        )
        if result:
            return  # Bảng đã tồn tại
        
        # Tạo bảng tạm
        create_table_query = """
        CREATE TABLE IF NOT EXISTS stock_db.ohlc_vnstock_temp
        (
            symbol String,
            time DateTime64(3),
            interval String,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume UInt64,
            total_gross_trade_amount Float64
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(time)
        ORDER BY (symbol, interval, time)
        SETTINGS index_granularity = 8192
        """
        CH_CLIENT.execute(create_table_query)
        print(f"   Created temporary table: ohlc_vnstock_temp")
    except Exception as e:
        print(f"  WARNING: Error creating temp table: {e}")
        raise

def insert_batch_to_clickhouse(batch_data):
    """
    Insert batch data vào ClickHouse
    Vì bảng ohlc là AggregatingMergeTree, không thể insert state functions trực tiếp
    Giải pháp: Insert vào bảng tạm (MergeTree) trước, sau đó dùng INSERT SELECT để chuyển vào ohlc
    """
    if not batch_data:
        return
    
    try:
        # Tạo bảng tạm nếu chưa có
        create_temp_table_if_not_exists()
        
        # Kiểm tra schema của bảng ohlc
        ohlc_schema = check_table_schema('ohlc')
        if not ohlc_schema:
            raise Exception("Cannot find ohlc table")
        
        use_trade_count = ohlc_schema.get('has_trade_count', False)
        is_aggregating = 'AggregatingMergeTree' in str(ohlc_schema.get('engine', ''))
        
        print(f"   Target table: ohlc (engine: {ohlc_schema.get('engine')}, has trade_count: {use_trade_count})")
        
        # Insert vào bảng tạm trước (MergeTree - có thể insert giá trị trực tiếp)
        values_list = []
        for row in batch_data:
            symbol, time, interval, open_val, high_val, low_val, close_val, volume_val, trade_count, total_gross_trade_amount = row
            # Format time cho SQL (DateTime)
            if isinstance(time, datetime):
                time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = str(time)
            
            # Escape single quotes trong symbol
            symbol_escaped = symbol.replace("'", "''")
            
            # Insert giá trị trực tiếp vào bảng tạm (không dùng state functions)
            values_list.append(
                f"('{symbol_escaped}', '{time_str}', '{interval}', "
                f"{open_val}, {high_val}, {low_val}, {close_val}, "
                f"{volume_val}, {total_gross_trade_amount})"
            )
        
        values_sql = ", ".join(values_list)
        
        # Insert vào bảng tạm
        insert_temp_query = f"""
            INSERT INTO stock_db.ohlc_vnstock_temp 
            (symbol, time, interval, open, high, low, close, volume, total_gross_trade_amount)
            VALUES {values_sql}
        """
        CH_CLIENT.execute(insert_temp_query)
        
        # Nếu ohlc là AggregatingMergeTree, cần chuyển từ temp table sang ohlc bằng INSERT SELECT
        if is_aggregating:
            # Chuyển từ temp table sang ohlc với state functions
            if use_trade_count:
                transfer_query = """
                    INSERT INTO stock_db.ohlc 
                    (symbol, time, interval, open, high, low, close, volume, trade_count, total_gross_trade_amount)
                    SELECT
                        symbol,
                        time,
                        interval,
                        argMinState(open, toDateTime64(time, 3)) AS open,
                        maxState(high) AS high,
                        minState(low) AS low,
                        argMaxState(close, toDateTime64(time, 3)) AS close,
                        sumState(volume) AS volume,
                        countState() AS trade_count,
                        sumState(total_gross_trade_amount) AS total_gross_trade_amount
                    FROM stock_db.ohlc_vnstock_temp
                    GROUP BY symbol, time, interval
                """
            else:
                transfer_query = """
                    INSERT INTO stock_db.ohlc 
                    (symbol, time, interval, open, high, low, close, volume, total_gross_trade_amount)
                    SELECT
                        symbol,
                        time,
                        interval,
                        argMinState(open, time) AS open,
                        maxState(high) AS high,
                        minState(low) AS low,
                        argMaxState(close, time) AS close,
                        sumState(volume) AS volume,
                        sumState(total_gross_trade_amount) AS total_gross_trade_amount
                    FROM stock_db.ohlc_vnstock_temp
                    GROUP BY symbol, time, interval
                """
            
            CH_CLIENT.execute(transfer_query)
            
            # Xóa dữ liệu đã chuyển từ temp table (optional, để tiết kiệm dung lượng)
            # CH_CLIENT.execute("TRUNCATE TABLE stock_db.ohlc_vnstock_temp")
        else:
            # Nếu ohlc không phải AggregatingMergeTree, copy trực tiếp
            if use_trade_count:
                transfer_query = """
                    INSERT INTO stock_db.ohlc 
                    (symbol, time, interval, open, high, low, close, volume, trade_count, total_gross_trade_amount)
                    SELECT
                        symbol,
                        time,
                        interval,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        1 AS trade_count,  -- Mặc định 1 vì không có thông tin từ vnstock
                        total_gross_trade_amount
                    FROM stock_db.ohlc_vnstock_temp
                """
            else:
                transfer_query = """
                    INSERT INTO stock_db.ohlc 
                    (symbol, time, interval, open, high, low, close, volume, total_gross_trade_amount)
                    SELECT
                        symbol,
                        time,
                        interval,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        total_gross_trade_amount
                    FROM stock_db.ohlc_vnstock_temp
                """
            
            CH_CLIENT.execute(transfer_query)
            CH_CLIENT.execute("TRUNCATE TABLE stock_db.ohlc_vnstock_temp")
            print("  🧹 Bảng tạm đã được làm sạch cho batch tiếp theo.")
    except Exception as e:
        print(f"   Error inserting batch: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_symbols_from_file(file_path='symbol.txt'):
    """
    Lấy danh sách symbols từ file text (mỗi dòng một symbol)
    
    Args:
        file_path: Đường dẫn đến file chứa symbols
    
    Returns:
        List of symbols (đã loại bỏ trùng lặp và dòng trống)
    """
    try:
        if not os.path.exists(file_path):
            print(f"WARNING: File {file_path} không tồn tại!")
            return []
        
        symbols = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Loại bỏ khoảng trắng và ký tự xuống dòng
                symbol = line.strip().upper()
                # Bỏ qua dòng trống
                if symbol:
                    symbols.append(symbol)
        
        # Loại bỏ trùng lặp nhưng giữ nguyên thứ tự
        seen = set()
        unique_symbols = []
        for symbol in symbols:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)
        
        if len(symbols) != len(unique_symbols):
            print(f"  WARNING: Đã loại bỏ {len(symbols) - len(unique_symbols)} symbols trùng lặp")
        
        return unique_symbols
    except Exception as e:
        print(f" Error reading symbols from file {file_path}: {e}")
        return []

def main():
    print("="*70)
    print("DOWNLOAD DATA NGAY 22-12-2025 TU VNSTOCK")
    print("="*70)

    # Kiểm tra vnstock
    if not check_vnstock_installed():
        sys.exit(1)

    #  CHỈ LẤY SYMBOL TỪ FILE symbol.txt
    print(f"\n Đọc symbols từ file symbol.txt...")
    symbols = get_symbols_from_file('symbol.txt')

    print(f" Đọc được {len(symbols)} symbols")
    print(f"   Sample: {', '.join(symbols[:10])}")
    if len(symbols) > 10:
        print(f"   ... và {len(symbols) - 10} symbols khác")

    print("\n" + "="*70)

    success_count = 0
    failed_symbols = []
    no_data_symbols = []

    total_symbols = len(symbols)
    start_time = time.time()

    print(f"\n Bắt đầu xử lý {total_symbols} symbols...")
    print(f" Có thể dừng bằng Ctrl+C\n")

    # Xử lý từng symbol
    for idx, symbol in enumerate(symbols, 1):
        try:
            print(f"\n{'='*70}")
            print(f"[{idx}/{total_symbols}] Xử lý {symbol}")
            print(f"{'='*70}")
            
            # Lấy dữ liệu từ vnstock
            df = get_latest_data_vnstock(symbol)
            
            if df is None or df.empty:
                print(f"  WARNING: Không có dữ liệu cho {symbol}")
                no_data_symbols.append(symbol)
                continue
            
            # Insert vào ClickHouse
            success = insert_vnstock_data_to_clickhouse(df, symbol)
            
            if success:
                success_count += 1
                print(f"   Thành công: {symbol}")
            else:
                failed_symbols.append(symbol)
                print(f"   Thất bại: {symbol}")
            
            # Nghỉ một chút để tránh rate limit
            if idx < total_symbols:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\nWARNING: Đã dừng bởi người dùng (Ctrl+C)")
            print(f"   Đã xử lý: {idx-1}/{total_symbols} symbols")
            break
        except Exception as e:
            print(f"\n   Lỗi khi xử lý {symbol}: {e}")
            failed_symbols.append(symbol)
            import traceback
            traceback.print_exc()
            continue
    
    # Tóm tắt kết quả
    elapsed_time = time.time() - start_time
    print(f"\n{'='*70}")
    print("KẾT QUẢ")
    print(f"{'='*70}")
    print(f" Thành công: {success_count}/{total_symbols}")
    print(f" Thất bại: {len(failed_symbols)}")
    print(f"WARNING: Không có dữ liệu: {len(no_data_symbols)}")
    print(f" Thời gian: {elapsed_time:.2f} giây")
    
    if failed_symbols:
        print(f"\n Symbols thất bại: {', '.join(failed_symbols)}")
    if no_data_symbols:
        print(f"\nWARNING: Symbols không có dữ liệu: {', '.join(no_data_symbols)}")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()

