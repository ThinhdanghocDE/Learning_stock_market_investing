"""
Test script để kiểm tra websocket_server.py
"""

import sys
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

print("=" * 60)
print("Testing WebSocket Server Dependencies")
print("=" * 60)

# Test 1: Check ClickHouse connection
print("\n1. Testing ClickHouse connection...")
try:
    result = CH_CLIENT.execute("SELECT 1")
    print("   [OK] ClickHouse connection OK")
except Exception as e:
    print(f"   [ERROR] ClickHouse connection failed: {e}")
    sys.exit(1)

# Test 2: Check ohlc table exists
print("\n2. Checking ohlc table...")
try:
    result = CH_CLIENT.execute("SELECT count() FROM stock_db.ohlc")
    count = result[0][0]
    print(f"   [OK] ohlc table exists, rows: {count}")
except Exception as e:
    print(f"   [ERROR] Error querying ohlc: {e}")
    sys.exit(1)

# Test 3: Test query with merge functions
print("\n3. Testing query with merge functions...")
try:
    query = """
    SELECT 
        symbol,
        time,
        argMinMerge(open) AS open,
        maxMerge(high) AS high,
        minMerge(low) AS low,
        argMaxMerge(close) AS close,
        sumMerge(volume) AS volume
    FROM stock_db.ohlc
    WHERE interval = '1m'
    GROUP BY symbol, time
    ORDER BY time DESC
    LIMIT 5
    """
    rows = CH_CLIENT.execute(query)
    print(f"   [OK] Query OK, found {len(rows)} rows")
    if rows:
        print(f"   Sample: {rows[0][0]} at {rows[0][1]}")
except Exception as e:
    print(f"   [ERROR] Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check websockets library
print("\n4. Checking websockets library...")
try:
    import websockets
    print("   [OK] websockets library OK")
except ImportError:
    print("   [ERROR] websockets library not found")
    print("   Install: pip install websockets")
    sys.exit(1)

# Test 5: Check asyncio
print("\n5. Checking asyncio...")
try:
    import asyncio
    print("   [OK] asyncio OK")
except ImportError:
    print("   [ERROR] asyncio not found")
    sys.exit(1)

print("\n" + "=" * 60)
print("[OK] All tests passed! WebSocket server should work.")
print("=" * 60)

