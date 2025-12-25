"""
ClickHouse Repository - Data Access Layer
"""

from clickhouse_driver import Client
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class ClickHouseRepository:
    """ClickHouse repository"""
    
    def __init__(self, client: Client):
        self.client = client
    
    def get_symbols(self, limit: Optional[int] = None) -> List[str]:
        """
        Lấy danh sách symbols từ ClickHouse
        Ưu tiên lấy từ bảng symbols (đầy đủ hơn), sau đó merge với symbols từ ohlc
        """
        all_symbols = set()
        
        # 1. Lấy từ bảng symbols (đầy đủ hơn, có thông tin công ty)
        try:
            query = "SELECT DISTINCT symbol FROM stock_db.symbols WHERE status = 'ACTIVE' ORDER BY symbol"
            result = self.client.execute(query)
            symbols_from_table = [row[0] for row in result]
            all_symbols.update(symbols_from_table)
        except Exception as e:
            print(f"Error querying symbols from symbols table: {e}")
        
        # 2. Lấy từ bảng ohlc (có dữ liệu thực tế) để bổ sung
        try:
            query = "SELECT DISTINCT symbol FROM stock_db.ohlc ORDER BY symbol"
            result = self.client.execute(query)
            symbols_from_ohlc = [row[0] for row in result]
            all_symbols.update(symbols_from_ohlc)
        except Exception as e:
            print(f"Error querying symbols from ohlc: {e}")
        
        # 3. Sắp xếp và giới hạn nếu cần
        sorted_symbols = sorted(list(all_symbols))
        
        if limit:
            return sorted_symbols[:limit]
        
        return sorted_symbols
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Lấy thông tin chi tiết của một symbol từ bảng symbols
        """
        try:
            query = """
                SELECT symbol, company_name, sector, industry, exchange, lot_size, isin, status
                FROM stock_db.symbols
                WHERE symbol = %(symbol)s AND status = 'ACTIVE'
                LIMIT 1
            """
            result = self.client.execute(query, {'symbol': symbol})
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    'symbol': row[0],
                    'company_name': row[1] or '',
                    'sector': row[2] or '',
                    'industry': row[3] or '',
                    'exchange': row[4] or '',
                    'lot_size': row[5] or 100,
                    'isin': row[6] or '',
                    'status': row[7] or 'ACTIVE'
                }
        except Exception as e:
            print(f"Error querying symbol info: {e}")
        
        return None
    
    def get_ohlc_historical(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1m",
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Lấy dữ liệu OHLC lịch sử từ ClickHouse
        
        Args:
            symbol: Mã chứng khoán
            start_time: Thời gian bắt đầu
            end_time: Thời gian kết thúc
            interval: Interval (1m, 5m, 1h, 1d)
            limit: Giới hạn số lượng records
        """
        # ClickHouse không hỗ trợ named parameters như PostgreSQL
        # Cần dùng string formatting, nhưng cần escape để tránh SQL injection
        # Format datetime
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Escape symbol và interval (basic protection)
        symbol_escaped = symbol.replace("'", "''")
        interval_escaped = interval.replace("'", "''")
        
        # Query với subquery để tính VWAP sau khi merge
        # ClickHouse không cho phép dùng merge functions nhiều lần trong CASE
        query = f"""
        SELECT
            symbol,
            time,
            interval,
            open,
            high,
            low,
            close,
            volume,
            total_gross_trade_amount,
            CASE 
                WHEN volume > 0 
                THEN total_gross_trade_amount / volume
                ELSE 0 
            END AS vwap
        FROM (
            SELECT
                symbol,
                time,
                interval,
                argMinMerge(open) AS open,
                maxMerge(high) AS high,
                minMerge(low) AS low,
                argMaxMerge(close) AS close,
                sumMerge(volume) AS volume,
                sumMerge(total_gross_trade_amount) AS total_gross_trade_amount
            FROM stock_db.ohlc
            WHERE symbol = '{symbol_escaped}'
                AND interval = '{interval_escaped}'
                AND time >= '{start_time_str}'
                AND time <= '{end_time_str}'
            GROUP BY symbol, time, interval
        )
        ORDER BY time DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        result = self.client.execute(query)
        
        # Convert to list of dicts
        columns = [
            "symbol", "time", "interval", "open", "high", "low", "close",
            "volume", "total_gross_trade_amount", "vwap"
        ]
        
        # Convert datetime objects to ISO format strings (UTC+7)
        def format_row(row):
            row_dict = dict(zip(columns, row))
            # Convert datetime to ISO string (assume UTC+7 from ClickHouse)
            if isinstance(row_dict.get('time'), datetime):
                # ClickHouse datetime đã là UTC+7 (naive), format thành ISO string
                # Format: "YYYY-MM-DDTHH:MM:SS" (naive, sẽ được frontend parse là UTC+7)
                row_dict['time'] = row_dict['time'].isoformat()
            return row_dict
        
        return [format_row(row) for row in result]
    
    def get_latest_ohlc(self, symbol: str, interval: str = "1m", limit: int = 100) -> List[Dict]:
        """
        Lấy OHLC data mới nhất
        Returns: List các candle mới nhất, sắp xếp theo time DESC (mới nhất trước)
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # 7 ngày gần nhất
        
        symbol_escaped = symbol.replace("'", "''")
        interval_escaped = interval.replace("'", "''")
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Query để lấy candle mới nhất (ORDER BY time DESC)
        query = f"""
        SELECT
            symbol,
            time,
            interval,
            open,
            high,
            low,
            close,
            volume,
            total_gross_trade_amount,
            CASE 
                WHEN volume > 0 
                THEN total_gross_trade_amount / volume
                ELSE 0 
            END AS vwap
        FROM (
            SELECT
                symbol,
                time,
                interval,
                argMinMerge(open) AS open,
                maxMerge(high) AS high,
                minMerge(low) AS low,
                argMaxMerge(close) AS close,
                sumMerge(volume) AS volume,
                sumMerge(total_gross_trade_amount) AS total_gross_trade_amount
            FROM stock_db.ohlc
            WHERE symbol = '{symbol_escaped}'
                AND interval = '{interval_escaped}'
                AND time >= '{start_time_str}'
                AND time <= '{end_time_str}'
            GROUP BY symbol, time, interval
        )
        ORDER BY time DESC
        LIMIT {limit}
        """
        
        try:
            result = self.client.execute(query)
            
            # Convert to list of dicts
            columns = [
                "symbol", "time", "interval", "open", "high", "low", "close",
                "volume", "total_gross_trade_amount", "vwap"
            ]
            
            def format_row(row):
                row_dict = dict(zip(columns, row))
                if isinstance(row_dict.get('time'), datetime):
                    row_dict['time'] = row_dict['time'].isoformat()
                return row_dict
            
            return [format_row(row) for row in result]
        except Exception as e:
            print(f"Error getting latest OHLC for {symbol}: {e}")
            return []
    
    def get_price_at_time(self, symbol: str, target_time: datetime, interval: str = "1m") -> Optional[float]:
        """
        Lấy giá tại một thời điểm cụ thể trong quá khứ
        Returns: Giá close của nến OHLC gần nhất trước hoặc tại target_time
        """
        # Tìm nến OHLC gần nhất trước hoặc tại target_time
        start_time = target_time - timedelta(days=1)  # Tìm trong 1 ngày trước đó
        end_time = target_time
        
        symbol_escaped = symbol.replace("'", "''")
        interval_escaped = interval.replace("'", "''")
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        query = f"""
        SELECT close
        FROM (
            SELECT
                symbol,
                time,
                interval,
                argMaxMerge(close) AS close
            FROM stock_db.ohlc
            WHERE symbol = '{symbol_escaped}'
                AND interval = '{interval_escaped}'
                AND time >= '{start_time_str}'
                AND time <= '{end_time_str}'
            GROUP BY symbol, time, interval
        )
        ORDER BY time DESC
        LIMIT 1
        """
        
        try:
            result = self.client.execute(query)
            if result and len(result) > 0:
                return float(result[0][0])
        except Exception as e:
            print(f"Error getting price at time for {symbol} at {target_time}: {e}")
        return None
    
    def get_top_symbols_by_candle_count(
        self, 
        interval: str = "1m",
        limit: int = 10,
        min_candles: int = 100
    ) -> List[Dict]:
        """
        Lấy danh sách các mã chứng khoán có nhiều nến nhất
        
        Args:
            interval: Interval của nến (1m, 5m, 1h, 1d)
            limit: Số lượng mã trả về
            min_candles: Số nến tối thiểu để được liệt kê
        
        Returns:
            List[Dict] với format: [{"symbol": "ACB", "candle_count": 1234}, ...]
        """
        interval_escaped = interval.replace("'", "''")
        
        query = f"""
        SELECT 
            symbol,
            count() AS candle_count
        FROM stock_db.ohlc
        WHERE interval = '{interval_escaped}'
        GROUP BY symbol
        HAVING candle_count >= {min_candles}
        ORDER BY candle_count DESC
        LIMIT {limit}
        """
        
        try:
            result = self.client.execute(query)
            return [
                {"symbol": row[0], "candle_count": int(row[1])}
                for row in result
            ]
        except Exception as e:
            print(f"Error getting top symbols by candle count: {e}")
            return []

