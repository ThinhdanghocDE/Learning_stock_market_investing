"""
Script để lấy dữ liệu intraday (trong ngày) từ vnstock
Chỉ lấy dữ liệu real-time trong ngày, không lấy historical data
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

def get_intraday_data_vnstock(symbol):
    """
    Lấy dữ liệu intraday (trong ngày) từ vnstock
    
    Args:
        symbol: Mã cổ phiếu (ví dụ: 'VIC', 'VNM', 'VCB')
    """
    try:
        from vnstock import Quote
        
        print(f"\nDang lay du lieu intraday cho {symbol}...")
        
        # Khởi tạo Quote object
        quote = Quote(symbol=symbol, source='VCI')
        
        # Chỉ lấy intraday data (real-time, trong ngày)
        print("   Lay intraday data (real-time, trong ngay)...")
        try:
            df_intraday = quote.intraday(symbol=symbol, page_size=10000, show_log=False)
            if df_intraday is not None and not df_intraday.empty:
                print(f"      Lay duoc {len(df_intraday)} records tu intraday")
                if isinstance(df_intraday.index, pd.DatetimeIndex):
                    print(f"     Latest time: {df_intraday.index[-1]}")
                elif 'time' in df_intraday.columns:
                    print(f"     Latest time: {df_intraday['time'].max()}")
                return df_intraday
            else:
                print(f"     WARNING: Khong co du lieu intraday")
                return None
        except Exception as e:
            print(f"     WARNING: Khong the lay intraday: {e}")
            return None
        
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

def filter_today_data(df):
    """
    Filter chỉ lấy dữ liệu trong ngày hiện tại
    
    Args:
        df: DataFrame với index là DatetimeIndex hoặc có cột 'time'
    
    Returns:
        DataFrame đã được filter chỉ còn dữ liệu trong ngày
    """
    if df is None or df.empty:
        return df
    
    try:
        # Lấy ngày hiện tại (UTC+7)
        vn_timezone = timezone(timedelta(hours=7))
        today = datetime.now(vn_timezone).date()
        
        # Nếu index là DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            df_filtered = df[df.index.date == today]
        # Nếu có cột 'time'
        elif 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], errors='coerce')
            df = df.dropna(subset=['time'])
            df_filtered = df[df['time'].dt.date == today]
        else:
            # Không có thông tin thời gian, giữ nguyên
            print(f"  WARNING: Khong co thong tin thoi gian, giu nguyen toan bo du lieu")
            return df
        
        print(f"  📅 Filter du lieu trong ngay {today}: {len(df_filtered)}/{len(df)} records")
        return df_filtered
        
    except Exception as e:
        print(f"  WARNING: Loi khi filter du lieu trong ngay: {e}")
        return df

def insert_vnstock_data_to_clickhouse(df, symbol):
    """
    Insert dữ liệu intraday từ vnstock DataFrame vào ClickHouse bảng ohlc
    
    Args:
        df: DataFrame từ vnstock (intraday format)
        symbol: Mã cổ phiếu
    """
    if df is None or df.empty:
        return False
    
    try:
        print(f"\nDang insert {len(df)} records vao ClickHouse...")
        
        # Filter chỉ lấy dữ liệu trong ngày
        df = filter_today_data(df)
        
        if df is None or df.empty:
            print(f"  WARNING: Khong co du lieu trong ngay de insert")
            return False
        
        inserted = 0
        skipped = 0
        batch_data = []  # Batch insert để tăng performance
        
        # Kiểm tra xem là intraday data format
        # Intraday có columns: ['time', 'price', 'volume', 'match_type', 'id']
        is_intraday = 'price' in df.columns and ('time' in df.columns or isinstance(df.index, pd.DatetimeIndex))
        
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
            print(f"  WARNING: Warning: Khong phai intraday format, thu xu ly nhu historical...")
            # Đảm bảo index là DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                print(f"     Converting index to DatetimeIndex...")
                try:
                    df.index = pd.to_datetime(df.index, errors='coerce')
                    df = df.dropna(subset=[df.columns[0]])
                    print(f"      Converted to DatetimeIndex, {len(df)} valid records remaining")
                except Exception as e:
                    print(f"     WARNING: Error converting index: {e}")
                    return False
        
        # Đảm bảo index là DatetimeIndex trước khi xử lý
        if not isinstance(df.index, pd.DatetimeIndex):
            print(f"   Error: Index is not DatetimeIndex after processing")
            return False
        
        # Filter lại chỉ lấy dữ liệu trong ngày (sau khi aggregate)
        df = filter_today_data(df)
        if df is None or df.empty:
            print(f"  WARNING: Khong co du lieu trong ngay sau khi aggregate")
            return False
        
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
                elif isinstance(timestamp, datetime):
                    pass  # Đã là datetime
                else:
                    timestamp = pd.to_datetime(timestamp).to_pydatetime()
                
                # Validate timestamp (chỉ lấy trong ngày)
                vn_timezone = timezone(timedelta(hours=7))
                today = datetime.now(vn_timezone).date()
                if timestamp.date() != today:
                    skipped += 1
                    continue
                
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
                
                # Tính total_gross_trade_amount
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
    """
    try:
        result = CH_CLIENT.execute(f"DESCRIBE TABLE stock_db.{table_name}")
        columns = {row[0]: row[1] for row in result}
        
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
    """
    try:
        result = CH_CLIENT.execute(
            "SELECT name FROM system.tables WHERE database = 'stock_db' AND name = 'ohlc_vnstock_temp'"
        )
        if result:
            return  # Bảng đã tồn tại
        
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
    """
    if not batch_data:
        return
    
    try:
        create_temp_table_if_not_exists()
        
        ohlc_schema = check_table_schema('ohlc')
        if not ohlc_schema:
            raise Exception("Cannot find ohlc table")
        
        use_trade_count = ohlc_schema.get('has_trade_count', False)
        is_aggregating = 'AggregatingMergeTree' in str(ohlc_schema.get('engine', ''))
        
        print(f"   Target table: ohlc (engine: {ohlc_schema.get('engine')}, has trade_count: {use_trade_count})")
        
        # Insert vào bảng tạm trước
        values_list = []
        for row in batch_data:
            symbol, time, interval, open_val, high_val, low_val, close_val, volume_val, trade_count, total_gross_trade_amount = row
            if isinstance(time, datetime):
                time_str = time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = str(time)
            
            symbol_escaped = symbol.replace("'", "''")
            
            values_list.append(
                f"('{symbol_escaped}', '{time_str}', '{interval}', "
                f"{open_val}, {high_val}, {low_val}, {close_val}, "
                f"{volume_val}, {total_gross_trade_amount})"
            )
        
        values_sql = ", ".join(values_list)
        
        insert_temp_query = f"""
            INSERT INTO stock_db.ohlc_vnstock_temp 
            (symbol, time, interval, open, high, low, close, volume, total_gross_trade_amount)
            VALUES {values_sql}
        """
        CH_CLIENT.execute(insert_temp_query)
        
        # Chuyển từ temp table sang ohlc
        if is_aggregating:
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
        else:
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
                        1 AS trade_count,
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

def get_allowed_symbols():
    """
    Lấy danh sách 30 mã cổ phiếu được phép
    
    Returns:
        List of symbols
    """
    return [
        'BSR', 'CEO', 'HPG', 'MBB', 'VPB', 'SHB', 'FPT', 'MSN', 'TCB', 'STB',
        'CTG', 'VNM', 'ACB', 'DGC', 'DBC', 'VCB', 'HDB', 'DCM', 'BID', 'CII',
        'EIB', 'BAF', 'GAS', 'LPB', 'CTD', 'CTS', 'AAA', 'ANV', 'CSV', 'DDV'
    ]

def main():
    """Main function"""
    print("="*70)
    print("DOWNLOAD DATA INTRADAY TU VNSTOCK (CHI LAY DU LIEU TRONG NGAY)")
    print("="*70)
    
    # Kiểm tra vnstock
    if not check_vnstock_installed():
        sys.exit(1)
    
    # Lấy symbols từ command line hoặc dùng 30 mã mặc định
    if len(sys.argv) > 1:
        # Symbols từ command line (chỉ lấy các mã trong danh sách được phép)
        allowed_symbols = get_allowed_symbols()
        requested_symbols = [s.upper() for s in sys.argv[1:]]
        symbols = [s for s in requested_symbols if s in allowed_symbols]
        
        if len(symbols) < len(requested_symbols):
            invalid = [s for s in requested_symbols if s not in allowed_symbols]
            print(f"\nWARNING: Một số mã không trong danh sách được phép: {', '.join(invalid)}")
        
        print(f"\n Sử dụng symbols từ command line: {', '.join(symbols)}")
    else:
        # Mặc định: Lấy 30 mã được phép
        symbols = get_allowed_symbols()
        print(f" Sử dụng 30 mã được phép:")
        print(f"   {', '.join(symbols)}")
    
    if not symbols:
        print("\n Không có symbols nào để xử lý!")
        print("\nCách dùng:")
        print("   python download_vnstock_intraday.py              # Lấy tất cả 30 mã được phép")
        print("   python download_vnstock_intraday.py ACB VIC VNM # Chỉ lấy ACB, VIC, VNM (nếu trong danh sách)")
        sys.exit(1)
    
    print("\n" + "="*70)
    
    success_count = 0
    failed_symbols = []
    no_data_symbols = []
    
    total_symbols = len(symbols)
    start_time = time.time()
    
    print(f"\n Bắt đầu xử lý {total_symbols} symbols...")
    print(f"📅 Chỉ lấy dữ liệu trong ngày hiện tại")
    print(f" Có thể dừng bằng Ctrl+C và tiếp tục sau\n")
    
    for idx, symbol in enumerate(symbols, 1):
        try:
            if idx % 10 == 0 or idx == 1:
                elapsed = time.time() - start_time
                if idx > 1:
                    avg_time = elapsed / (idx - 1)
                    remaining = (total_symbols - idx + 1) * avg_time
                    print(f"\n[{idx}/{total_symbols}] Progress: {idx/total_symbols*100:.1f}% | "
                          f"Elapsed: {elapsed/60:.1f}m | Est. remaining: {remaining/60:.1f}m | "
                          f"Success: {success_count}")
            
            print(f"\n[{idx}/{total_symbols}] Processing: {symbol}")
            print(f"{'='*70}")
            
            # Lấy dữ liệu intraday
            df = get_intraday_data_vnstock(symbol)
            
            if df is not None and not df.empty:
                # Insert vào ClickHouse
                success = insert_vnstock_data_to_clickhouse(df, symbol)
                
                if success:
                    success_count += 1
                    print(f" {symbol}: Thành công!")
                else:
                    print(f" {symbol}: Thất bại khi insert")
                    failed_symbols.append(symbol)
            else:
                print(f"WARNING: {symbol}: Không có dữ liệu intraday")
                no_data_symbols.append(symbol)
            
            # Đợi một chút giữa các requests để tránh rate limit
            if idx < total_symbols:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\nWARNING:  Dừng bởi người dùng tại symbol {idx}/{total_symbols}: {symbol}")
            print(f" Đã xử lý: {success_count} thành công, {len(failed_symbols)} thất bại, {len(no_data_symbols)} không có dữ liệu")
            break
        except Exception as e:
            print(f"\n Lỗi khi xử lý {symbol}: {e}")
            failed_symbols.append(symbol)
            continue
    
    # Tóm tắt
    elapsed_total = time.time() - start_time
    print(f"\n{'='*70}")
    print("TÓM TẮT")
    print(f"{'='*70}")
    print(f" Thành công: {success_count}/{total_symbols} symbols")
    print(f" Thất bại: {len(failed_symbols)} symbols")
    print(f"WARNING:  Không có dữ liệu: {len(no_data_symbols)} symbols")
    print(f"  Tổng thời gian: {elapsed_total/60:.1f} phút")
    
    if failed_symbols:
        print(f"\n Symbols thất bại ({len(failed_symbols)}):")
        for sym in failed_symbols[:20]:
            print(f"   - {sym}")
        if len(failed_symbols) > 20:
            print(f"   ... và {len(failed_symbols) - 20} symbols khác")
    
    if no_data_symbols:
        print(f"\nWARNING:  Symbols không có dữ liệu ({len(no_data_symbols)}):")
        for sym in no_data_symbols[:20]:
            print(f"   - {sym}")
        if len(no_data_symbols) > 20:
            print(f"   ... và {len(no_data_symbols) - 20} symbols khác")
    
    if success_count > 0:
        print(f"\n Dữ liệu intraday đã được insert vào ClickHouse!")
        print("Dữ liệu đã ở đúng nơi (ClickHouse ohlc table)")
        print("\nKiểm tra dữ liệu:")
        print("  docker exec clickhouse clickhouse-client --query \"SELECT symbol, MAX(time) FROM stock_db.ohlc WHERE interval='1m' GROUP BY symbol LIMIT 10\"")

if __name__ == "__main__":
    main()

