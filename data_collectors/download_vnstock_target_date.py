"""
VNStock ETL - Historical 1m data
Target date: 2025-12-22
Symbols: fixed 30 symbols
"""

import os
import time
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from vnstock import Quote
from clickhouse_driver import Client as CHClient

# =========================
# Config
# =========================

load_dotenv()

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 9000))
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "stock_db")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

TARGET_DATE = "2025-12-05"

ALLOWED_SYMBOLS = {
    # 'BSR', 'CEO', 'HPG', 'MBB', 'VPB', 'SHB', 'FPT', 'MSN', 'TCB', 'STB',
    # 'CTG', 'VNM', 'ACB', 'DGC', 'DBC', 'VCB', 'HDB', 'DCM', 'BID', 'CII',
    # 'EIB', 'BAF', 'GAS', 'LPB', 'CTD', 'CTS', 'AAA', 'ANV', 'CSV', 'DDV'
    'DGC'
}

TABLE_NAME = "ohlc_1m_raw"

# =========================
# ClickHouse
# =========================

ch_client = CHClient(
    host=CLICKHOUSE_HOST,
    port=CLICKHOUSE_PORT,
    database=CLICKHOUSE_DB,
    user=CLICKHOUSE_USER,
    password=CLICKHOUSE_PASSWORD
)

# =========================
# Extract
# =========================

def fetch_1m_data(symbol: str) -> pd.DataFrame:
    print(f"[INFO] Fetching data for {symbol}")

    quote = Quote(symbol=symbol, source="VCI")

    df = quote.history(
        start=TARGET_DATE,
        end=TARGET_DATE,
        interval="1m"
    )

    if df is None or df.empty:
        print(f"[WARN] No data returned for {symbol}")
        return pd.DataFrame()

    df.index = pd.to_datetime(df.index)
    df = df[df.index.strftime("%Y-%m-%d") == TARGET_DATE]

    return df

# =========================
# Transform
# =========================

def transform_df(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.reset_index().rename(columns={"index": "timestamp"})
    df["symbol"] = symbol

    df = df[[
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]]

    return df

# =========================
# Load
# =========================

def load_to_clickhouse(df: pd.DataFrame):
    if df.empty:
        return

    records = list(df.itertuples(index=False, name=None))

    query = f"""
        INSERT INTO {TABLE_NAME}
        (timestamp, symbol, open, high, low, close, volume)
        VALUES
    """

    ch_client.execute(query, records)
    print(f"[INFO] Inserted {len(records)} rows")

# =========================
# Main ETL
# =========================

def main():
    print("=" * 60)
    print("VNSTOCK ETL - HISTORICAL 1M DATA")
    print(f"Target date: {TARGET_DATE}")
    print(f"Symbols count: {len(ALLOWED_SYMBOLS)}")
    print("=" * 60)

    for symbol in sorted(ALLOWED_SYMBOLS):
        try:
            df_raw = fetch_1m_data(symbol)
            df_transformed = transform_df(df_raw, symbol)
            load_to_clickhouse(df_transformed)
            time.sleep(0.5)

        except Exception as e:
            print(f"[ERROR] Failed processing {symbol}: {e}")

    print("[INFO] ETL job finished")

# =========================
# Entry
# =========================

if __name__ == "__main__":
    main()
