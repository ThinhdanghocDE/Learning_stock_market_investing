"""
Script để kiểm tra các symbol trong ClickHouse có thể lấy được dữ liệu từ vnstock không
"""
import os
import sys
from dotenv import load_dotenv
from clickhouse_driver import Client
import time

# Fix encoding issue với vnstock
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from vnstock import Quote
except Exception as e:
    print(f"Cannot import vnstock: {e}")
    sys.exit(1)

load_dotenv()

# ClickHouse connection
CH_CLIENT = Client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    database=os.getenv("CLICKHOUSE_DB", "stock_db"),
    user=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD", "")
)

def get_symbols_from_clickhouse():
    """Lấy danh sách symbols từ ClickHouse"""
    try:
        result = CH_CLIENT.execute(
            "SELECT DISTINCT symbol FROM stock_db.symbols WHERE status = 'ACTIVE' ORDER BY symbol"
        )
        return [row[0] for row in result]
    except Exception as e:
        print(f"Error getting symbols from ClickHouse: {e}")
        return []

def test_vnstock_symbol(symbol):
    """Test xem vnstock có thể lấy được dữ liệu của symbol không"""
    try:
        quote = Quote(symbol=symbol, source='VCI')
        
        # Thử lấy historical data (7 ngày gần nhất để đảm bảo có dữ liệu)
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        df = quote.history(start=week_ago, end=today, interval='1m')
        
        if df is not None and not df.empty:
            return True, len(df)
        else:
            return False, "No data"
    except Exception as e:
        error_msg = str(e)
        # Rút gọn error message nếu quá dài
        if len(error_msg) > 50:
            error_msg = error_msg[:47] + "..."
        return False, error_msg

def main():
    print("="*70)
    print("KIỂM TRA SYMBOLS CÓ THỂ LẤY ĐƯỢC TỪ VNSTOCK")
    print("="*70)
    
    # Lấy symbols từ ClickHouse
    print("\nLấy danh sách symbols từ ClickHouse...")
    symbols = get_symbols_from_clickhouse()
    
    if not symbols:
        print("Không có symbols nào trong ClickHouse")
        return
    
    print(f"Tìm thấy {len(symbols)} symbols")
    print(f"   Sample: {', '.join(symbols[:10])}")
    
    # Test từng symbol
    print("\n" + "="*70)
    print("TESTING VNSTOCK API...")
    print("="*70)
    print(f"Sẽ test {len(symbols)} symbols. Quá trình này có thể mất vài phút...")
    print(f"Tip: Có thể dừng bằng Ctrl+C và tiếp tục sau")
    
    available_symbols = []
    unavailable_symbols = []
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols, 1):
        try:
            # Hiển thị progress mỗi 10 symbols
            if i % 10 == 0 or i == 1:
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(symbols) - i) * avg_time
                print(f"\n[{i}/{len(symbols)}] Progress: {i/len(symbols)*100:.1f}% | "
                      f"Elapsed: {elapsed/60:.1f}m | Est. remaining: {remaining/60:.1f}m")
            
            print(f"[{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
            success, result = test_vnstock_symbol(symbol)
            
            if success:
                print(f"OK ({result} records)")
                available_symbols.append(symbol)
            else:
                print(f"FAIL")
                unavailable_symbols.append((symbol, result))
            
            # Đợi một chút để tránh rate limit (giảm xuống 0.3s để nhanh hơn)
            time.sleep(0.3)
            
        except KeyboardInterrupt:
            print(f"\n\nInterrupted by user at symbol {i}/{len(symbols)}")
            print(f"Tested: {len(available_symbols)} available, {len(unavailable_symbols)} unavailable")
            break
        except Exception as e:
            print(f"Error: {e}")
            unavailable_symbols.append((symbol, str(e)))
            continue
    
    # Tóm tắt
    print("\n" + "="*70)
    print("TÓM TẮT")
    print("="*70)
    print(f"Có thể lấy được: {len(available_symbols)}/{len(symbols)} symbols")
    print(f"Không lấy được: {len(unavailable_symbols)}/{len(symbols)} symbols")
    
    if available_symbols:
        print(f"\nSymbols có thể lấy được ({len(available_symbols)} symbols):")
        # Hiển thị tất cả nếu < 50, nếu không thì hiển thị 50 đầu
        display_count = min(50, len(available_symbols))
        for symbol in available_symbols[:display_count]:
            print(f"   - {symbol}")
        if len(available_symbols) > display_count:
            print(f"   ... và {len(available_symbols) - display_count} symbols khác")
        
        # Lưu vào file
        try:
            with open('available_vnstock_symbols.txt', 'w', encoding='utf-8') as f:
                for symbol in available_symbols:
                    f.write(f"{symbol}\n")
            print(f"\nĐã lưu danh sách vào file: available_vnstock_symbols.txt")
        except Exception as e:
            print(f"Không thể lưu file: {e}")
    
    if unavailable_symbols:
        print(f"\nSymbols không lấy được ({len(unavailable_symbols)} symbols):")
        # Hiển thị 20 đầu với lý do
        for item in unavailable_symbols[:20]:
            if isinstance(item, tuple):
                symbol, reason = item
                print(f"   - {symbol}: {reason}")
            else:
                print(f"   - {item}")
        if len(unavailable_symbols) > 20:
            print(f"   ... và {len(unavailable_symbols) - 20} symbols khác")
    
    # Lưu kết quả
    if available_symbols:
        print(f"\nDanh sách đầy đủ symbols có thể lấy được đã được in ở trên")
        print(f"   Có thể dùng để chạy download_vnstock_latest.py")

if __name__ == "__main__":
    main()

