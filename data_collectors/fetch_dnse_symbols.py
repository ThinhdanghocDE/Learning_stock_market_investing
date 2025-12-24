"""
Script để lấy danh sách symbols từ vnstock và lưu vào ClickHouse bảng symbols
Sử dụng vnstock Company API để lấy thông tin chi tiết: https://vnstocks.com/docs/vnstock/thong-tin-cong-ty
"""
import os
from dotenv import load_dotenv
from clickhouse_driver import Client
from datetime import datetime
from vnstock import Listing, Company
import pandas as pd
import time

# =====================
# LOAD ENV
# =====================
load_dotenv()

# ClickHouse connection
CH_CLIENT = Client(
    host=os.getenv("CLICKHOUSE_HOST", "localhost"),
    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
    database=os.getenv("CLICKHOUSE_DB", "stock_db"),
    user=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD", "")
)

# =====================
# FETCH SYMBOLS FROM VNSTOCK
# =====================

def get_symbols_from_vnstock():
    """
    Lấy danh sách symbols từ vnstock
    
    Returns:
        DataFrame với thông tin symbols
    """
    try:
        print(" Fetching symbols from vnstock...")
        
        # Khởi tạo Listing object
        listing = Listing(source='VCI')  # Có thể dùng 'TCBS' nếu VCI không hoạt động
        
        # Thử lấy theo exchange với keyword argument
        all_symbols_list = []
        
        # Option: Chọn exchanges để fetch
        # Có thể set env variable: FETCH_EXCHANGES=HOSE,HNX hoặc HOSE hoặc HNX,UPCOM
        fetch_exchanges_env = os.getenv("FETCH_EXCHANGES", "HOSE,HNX,UPCOM")
        exchanges_to_fetch = [e.strip() for e in fetch_exchanges_env.split(',') if e.strip() in ['HOSE', 'HNX', 'UPCOM']]
        
        if not exchanges_to_fetch:
            exchanges_to_fetch = ['HOSE', 'HNX']  # Default: chỉ HOSE và HNX
        
        print(f"    Will fetch from: {', '.join(exchanges_to_fetch)}")
        
        for exchange in exchanges_to_fetch:
            try:
                print(f"   Fetching from {exchange}...")
                # Thử với keyword argument lang
                symbols = listing.symbols_by_exchange(exchange=exchange, lang='vi')
                if not symbols.empty:
                    # Thêm column exchange để phân biệt
                    symbols['exchange'] = exchange
                    all_symbols_list.append(symbols)
                    print(f"       Found {len(symbols)} symbols")
            except Exception as e:
                print(f"      WARNING: Error fetching {exchange}: {e}")
                # Thử không có lang parameter
                try:
                    symbols = listing.symbols_by_exchange(exchange)
                    if not symbols.empty:
                        symbols['exchange'] = exchange
                        all_symbols_list.append(symbols)
                        print(f"       Found {len(symbols)} symbols (without lang)")
                except Exception as e2:
                    print(f"       Failed: {e2}")
        
        if all_symbols_list:
            all_symbols = pd.concat(all_symbols_list, ignore_index=True)
            print(f" Fetched {len(all_symbols)} symbols from vnstock")
            
            # Filter: Chỉ lấy mã cổ phiếu thông thường (loại bỏ chứng quyền, phái sinh, etc.)
            # Kiểm tra column 'type' nếu có
            if 'type' in all_symbols.columns:
                print(f"\n    Symbol types distribution:")
                type_counts = all_symbols['type'].value_counts()
                for typ, count in type_counts.items():
                    print(f"      {typ}: {count} symbols")
                
                # Filter chỉ lấy mã cổ phiếu thông thường
                # HOSE thông thường có ~332 mã cổ phiếu, không phải 3159
                # 3159 bao gồm cả chứng quyền, phái sinh, ETF, etc.
                initial_count = len(all_symbols)
                
                # Option: Filter để chỉ lấy mã cổ phiếu thông thường
                filter_stocks_only = os.getenv("FILTER_STOCKS_ONLY", "false").lower() == "true"
                
                if filter_stocks_only:
                    # Filter theo type - loại bỏ chứng quyền, phái sinh, ETF
                    # Cần điều chỉnh dựa trên giá trị thực tế của 'type'
                    print(f"    Filtering to keep only regular stocks...")
                    
                    # Thử filter các type không mong muốn
                    # Loại bỏ các mã có type chứa: WARRANT, DERIVATIVE, CW, ETF, BOND
                    type_str = all_symbols['type'].astype(str).str.upper()
                    exclude_patterns = ['WARRANT', 'DERIVATIVE', 'CW', 'ETF', 'BOND', 'TRÁI PHIẾU', 'CHỨNG QUYỀN']
                    
                    mask = ~type_str.str.contains('|'.join(exclude_patterns), case=False, na=False)
                    all_symbols = all_symbols[mask]
                    
                    filtered_count = len(all_symbols)
                    removed = initial_count - filtered_count
                    print(f"    After filtering: {filtered_count} symbols (removed {removed} non-stock symbols)")
                else:
                    print(f"     All types kept (no filtering applied)")
                    print(f"    Set FILTER_STOCKS_ONLY=true to filter only regular stocks (~332 for HOSE)")
            
            # Check for duplicates
            duplicate_count = all_symbols.duplicated(subset=['symbol']).sum()
            if duplicate_count > 0:
                print(f"\n   WARNING: Found {duplicate_count} duplicate symbols (same symbol in multiple exchanges)")
                
                # Kiểm tra xem có phải cùng 1 symbol thực sự ở nhiều exchanges không
                duplicates_df = all_symbols[all_symbols.duplicated(subset=['symbol'], keep=False)]
                if not duplicates_df.empty:
                    print(f"    Sample duplicates:")
                    sample_dups = duplicates_df.groupby('symbol')['exchange'].apply(list).head(5)
                    for sym, exchanges in sample_dups.items():
                        print(f"      {sym}: {exchanges}")
                    
                    # Kiểm tra xem có phải vnstock trả về cùng data cho cả 3 exchanges không
                    unique_by_exchange = all_symbols.groupby('exchange')['symbol'].nunique()
                    print(f"\n    Unique symbols per exchange:")
                    for exch, count in unique_by_exchange.items():
                        print(f"      {exch}: {count} unique symbols")
                    
                    # Nếu số unique symbols giống nhau → có thể vnstock trả về cùng data
                    if len(unique_by_exchange.unique()) == 1:
                        print(f"\n   WARNING: WARNING:All exchanges have same number of unique symbols!")
                        print(f"      This suggests vnstock may return same data for all exchanges.")
                        print(f"       Solution: Fetch only from HOSE (or filter by type/product_grp_id)")
                
                # Strategy: Remove duplicates nhưng ưu tiên HOSE > HNX > UPCOM
                # Tạo priority column
                exchange_priority = {'HOSE': 1, 'HNX': 2, 'UPCOM': 3}
                all_symbols['priority'] = all_symbols['exchange'].map(exchange_priority)
                
                # Sort by priority và keep first (ưu tiên HOSE)
                all_symbols = all_symbols.sort_values('priority').drop_duplicates(subset=['symbol'], keep='first')
                all_symbols = all_symbols.drop(columns=['priority'])
                
                print(f"    After removing duplicates (priority: HOSE > HNX > UPCOM): {len(all_symbols)} unique symbols")
            
            return all_symbols
        else:
            raise Exception("No symbols fetched from any exchange")
        
    except Exception as e:
        print(f" Error fetching symbols from vnstock: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: Thử dùng all_symbols() nếu symbols_by_exchange() không hoạt động
        try:
            print("\nWARNING: Trying fallback method: all_symbols()...")
            listing = Listing(source='VCI')
            all_symbols = listing.all_symbols()
            if not all_symbols.empty:
                print(f" Fetched {len(all_symbols)} symbols using fallback method")
                print("   WARNING: Note: Fallback method may have limited information")
                return all_symbols
        except Exception as e2:
            print(f" Fallback method also failed: {e2}")
        
        return pd.DataFrame()

def get_company_info(symbol, source='TCBS'):
    """
    Lấy thông tin chi tiết công ty từ vnstock Company API
    Ref: https://vnstocks.com/docs/vnstock/thong-tin-cong-ty
    
    Args:
        symbol: Mã chứng khoán
        source: 'TCBS' hoặc 'VCI'
    
    Returns:
        dict với thông tin công ty hoặc None nếu lỗi
    """
    try:
        company = Company(symbol=symbol, source=source)
        overview = company.overview()
        
        if overview is not None and not overview.empty:
            row = overview.iloc[0]
            return {
                'symbol': symbol,
                'company_name': str(row.get('company_profile', row.get('organName', ''))).strip(),
                'sector': str(row.get('icb_name2', row.get('icb_name3', ''))).strip(),
                'industry': str(row.get('icb_name4', '')).strip(),
                'isin': str(row.get('id', '')).strip(),  # Có thể là ID, không phải ISIN
            }
    except Exception as e:
        # Silent fail để không làm gián đoạn quá trình
        pass
    return None

def normalize_symbol_data(row, company_info=None):
    """
    Normalize symbol data từ vnstock DataFrame sang ClickHouse schema
    
    Args:
        row: pandas Series từ vnstock DataFrame
        company_info: dict từ Company API (optional)
    
    Returns:
        dict với format chuẩn cho ClickHouse
    """
    try:
        # Extract symbol (có thể là 'symbol', 'code', 'ticker')
        symbol = str(row.get('symbol', row.get('code', row.get('ticker', '')))).strip()
        if not symbol:
            return None
        
        # Extract exchange
        # Ưu tiên lấy từ column 'exchange' nếu có (từ symbols_by_exchange)
        # DataFrame đã có column 'exchange' được set khi fetch
        exchange_raw = row.get('exchange')
        
        if exchange_raw:
            # Nếu là string, convert to uppercase
            if isinstance(exchange_raw, str):
                exchange = exchange_raw.upper()
            else:
                exchange = str(exchange_raw).upper()
            
            # Validate exchange
            if exchange not in ['HOSE', 'HNX', 'UPCOM']:
                # Fallback: parse từ string
                if 'HOSE' in exchange or 'STO' in exchange:
                    exchange = "HOSE"
                elif 'HNX' in exchange or 'STX' in exchange:
                    exchange = "HNX"
                elif 'UPCOM' in exchange or 'UPX' in exchange:
                    exchange = "UPCOM"
                else:
                    exchange = "HOSE"  # Default
        else:
            # Nếu không có column exchange, thử từ các field khác
            market_raw = str(row.get('market', row.get('organCode', ''))).upper()
            if market_raw and market_raw in ['HOSE', 'HNX', 'UPCOM']:
                exchange = market_raw
            elif 'HOSE' in market_raw or 'STO' in market_raw:
                exchange = "HOSE"
            elif 'HNX' in market_raw or 'STX' in market_raw:
                exchange = "HNX"
            elif 'UPCOM' in market_raw or 'UPX' in market_raw:
                exchange = "UPCOM"
            else:
                # Nếu không có thông tin, thử đoán từ symbol
                # HOSE thường có 3 ký tự, HNX có thể có 4, UPCOM có thể có 5+
                symbol_len = len(symbol) if symbol else 0
                if symbol_len <= 3:
                    exchange = "HOSE"  # Default cho HOSE
                elif symbol_len == 4:
                    exchange = "HNX"  # Có thể là HNX
                else:
                    exchange = "UPCOM"  # Có thể là UPCOM
        
        # Extract status
        status_raw = str(row.get('status', row.get('tradingStatus', 'ACTIVE'))).upper()
        if status_raw in ["ACTIVE", "SUSPENDED", "DELISTED"]:
            status = status_raw
        else:
            # Map các status khác
            if 'SUSPEND' in status_raw or 'NGUNG' in status_raw:
                status = "SUSPENDED"
            elif 'DELIST' in status_raw or 'HUY' in status_raw:
                status = "DELISTED"
            else:
                status = "ACTIVE"  # Default
        
        # Extract other fields - ưu tiên từ company_info nếu có
        if company_info:
            isin = company_info.get('isin', '')
            company_name = company_info.get('company_name', '') or str(row.get('organ_name', row.get('organName', row.get('companyName', '')))).strip()
            sector = company_info.get('sector', '') or str(row.get('icb_name2', row.get('icbSector', ''))).strip()
            industry = company_info.get('industry', '') or str(row.get('icb_name4', row.get('icbIndustry', ''))).strip()
        else:
            isin = str(row.get('isin', row.get('ISIN', ''))).strip()
            # Ưu tiên organ_name từ DataFrame
            company_name = str(row.get('organ_name', row.get('organName', row.get('companyName', row.get('company_name', row.get('name', '')))))).strip()
            sector = str(row.get('sector', row.get('industrySector', row.get('icbSector', row.get('icb_name2', ''))))).strip()
            industry = str(row.get('industry', row.get('industryGroup', row.get('icbIndustry', row.get('icb_name4', ''))))).strip()
        
        lot_size = int(row.get('lotSize', row.get('lot_size', 100)))
        
        return {
            "symbol": symbol,
            "isin": isin,
            "exchange": exchange,
            "lot_size": lot_size,
            "status": status,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "updated_at": datetime.now()
        }
    except Exception as e:
        print(f" Error normalizing symbol data for {row.get('symbol', 'unknown')}: {e}")
        return None

# =====================
# SAVE TO CLICKHOUSE
# =====================

def save_symbols_to_clickhouse(symbols_list):
    """
    Lưu danh sách symbols vào ClickHouse
    
    Args:
        symbols_list: List of normalized symbol dictionaries
    """
    if not symbols_list:
        print("WARNING: No symbols to save")
        return
    
    try:
        # Insert vào ClickHouse
        CH_CLIENT.execute(
            '''INSERT INTO stock_db.symbols 
               (symbol, isin, exchange, lot_size, status, company_name, sector, industry, updated_at) 
               VALUES''',
            [(s['symbol'], s['isin'], s['exchange'], s['lot_size'], s['status'],
              s['company_name'], s['sector'], s['industry'], s['updated_at'])
             for s in symbols_list if s is not None]
        )
        print(f" Saved {len(symbols_list)} symbols to ClickHouse")
    except Exception as e:
        print(f" Error saving symbols: {e}")
        import traceback
        traceback.print_exc()

def get_symbols_from_clickhouse():
    """
    Lấy danh sách symbols từ ClickHouse
    
    Returns:
        List of symbol strings
    """
    try:
        result = CH_CLIENT.execute(
            "SELECT symbol FROM stock_db.symbols WHERE status = 'ACTIVE' ORDER BY symbol"
        )
        return [row[0] for row in result]
    except Exception as e:
        print(f" Error getting symbols from ClickHouse: {e}")
        return []

# =====================
# MAIN
# =====================

def main():
    """Main function"""
    print(" Starting vnstock Symbols Fetcher...")
    
    # 1. Fetch symbols từ vnstock
    symbols_df = get_symbols_from_vnstock()
    
    if symbols_df.empty:
        print(" No symbols fetched. Exiting.")
        return
    
    print(f"\n Total symbols: {len(symbols_df)}")
    print(f"   Columns: {', '.join(symbols_df.columns.tolist())}")
    
    # Check exchange distribution BEFORE normalization
    if 'exchange' in symbols_df.columns:
        exchange_counts = symbols_df['exchange'].value_counts()
        print(f"\n   Exchange distribution (before normalization):")
        for exch, count in exchange_counts.items():
            print(f"      {exch}: {count} symbols")
        
        # Check for symbols in multiple exchanges
        symbol_exchange_counts = symbols_df.groupby('symbol')['exchange'].nunique()
        multi_exchange = symbol_exchange_counts[symbol_exchange_counts > 1]
        if len(multi_exchange) > 0:
            print(f"\n   WARNING: {len(multi_exchange)} symbols appear in multiple exchanges")
            print(f"      Sample: {', '.join(multi_exchange.head(5).index.tolist())}")
    
    # 2. Normalize data
    print("\n Normalizing symbol data...")
    print("   WARNING: Note: Using basic info from symbols_by_exchange().")
    print("    To get detailed info (sector, industry), use Company API (slower but more accurate)")
    
    # Option: Lấy thông tin chi tiết từ Company API (chậm hơn nhưng đầy đủ hơn)
    use_company_api = os.getenv("USE_COMPANY_API", "false").lower() == "true"
    
    normalized_symbols = []
    
    for idx, row in symbols_df.iterrows():
        symbol = str(row.get('symbol', row.get('code', row.get('ticker', '')))).strip()
        if not symbol:
            continue
        
        company_info = None
        if use_company_api:
            # Lấy thông tin chi tiết từ Company API (chậm)
            company_info = get_company_info(symbol, source='TCBS')
            # Rate limiting
            time.sleep(0.1)  # 100ms delay để tránh rate limit
        
        normalized = normalize_symbol_data(row, company_info=company_info)
        if normalized:
            normalized_symbols.append(normalized)
        
        # Progress indicator
        if (idx + 1) % 100 == 0:
            print(f"   Processed {idx + 1}/{len(symbols_df)} symbols...")
            if use_company_api:
                print(f"      (Using Company API - this will take longer)")
    
    print(f" Normalized {len(normalized_symbols)} symbols")
    
    if not normalized_symbols:
        print("WARNING: No symbols to save. Check normalization logic.")
        return
    
    # 3. Save to ClickHouse
    print("\n Saving to ClickHouse...")
    save_symbols_to_clickhouse(normalized_symbols)
    
    # 4. Verify
    print("\n Verification:")
    saved_symbols = get_symbols_from_clickhouse()
    print(f"   Total symbols in ClickHouse: {len(saved_symbols)}")
    
    if saved_symbols:
        print(f"   Sample symbols: {', '.join(saved_symbols[:10])}")
        
        # Statistics by exchange
        try:
            stats = CH_CLIENT.execute(
                "SELECT exchange, COUNT(*) as count FROM stock_db.symbols WHERE status = 'ACTIVE' GROUP BY exchange ORDER BY exchange"
            )
            print("\n   Statistics by exchange:")
            total = 0
            for exchange, count in stats:
                print(f"      {exchange}: {count} symbols")
                total += count
            print(f"      TOTAL: {total} symbols")
            
            # Check for potential duplicates (same symbol in multiple exchanges)
            duplicates = CH_CLIENT.execute(
                "SELECT symbol, COUNT(*) as cnt FROM stock_db.symbols WHERE status = 'ACTIVE' GROUP BY symbol HAVING cnt > 1"
            )
            if duplicates:
                print(f"\n   WARNING: Found {len(duplicates)} symbols appearing in multiple exchanges")
                print(f"      (This is normal if ReplacingMergeTree hasn't merged yet)")
        except Exception as e:
            print(f"   WARNING: Could not get statistics: {e}")
    
    print("\n Done!")

if __name__ == "__main__":
    main()

