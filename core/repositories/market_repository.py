# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.3.0 (Phase 7: PostgreSQL 全小寫相容與 Pandas 映射版)
#
# 📋 進版說明 (Version Notes):
#   1. [架構相容] 順應 PostgreSQL，SQL 語法全面改用小寫 (date, open...)。
#   2. [資料映射] 讀取資料後，透過 df.rename 自動將小寫欄位轉為首字母大寫 (Date, Open)，確保 UI 渲染正常。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組與資料庫連線
#   - 2️⃣ K 線資料讀取介面 (Query)
#   - 3️⃣ K 線資料寫入介面 (Command)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()

# ==========================================================
# 2️⃣ K 線資料讀取介面 (Query)
# ==========================================================
    def get_last_date(self, ticker: str) -> Optional[str]:
        # 全面改用小寫 date
        query = "SELECT MAX(date) as last_date FROM daily_price WHERE ticker = ?"
        try:
            result = self.db.fetch_one(query, (ticker,))
            return result['last_date'] if result and result['last_date'] else None
        except Exception:
            return None

    def get_historical_data_df(self, ticker: str) -> pd.DataFrame:
        # 全面改用小寫欄位查詢
        query = "SELECT date, open, high, low, close, volume FROM daily_price WHERE ticker = ? ORDER BY date ASC"
        try:
            rows = self.db.fetch_all(query, (ticker,))
            if not rows:
                return pd.DataFrame()
                
            df = pd.DataFrame(rows)
            
            # 🔥 關鍵修復：將 PostgreSQL 的小寫欄位，映射回 Pandas 所需的大寫欄位
            df.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            df.dropna(inplace=True)
            return df
        except Exception as e:
            logging.warning(f"讀取 {ticker} K 線資料失敗 (可能尚未下載或鎖定): {e}")
            return pd.DataFrame()

# ==========================================================
# 3️⃣ K 線資料寫入介面 (Command)
# ==========================================================
    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        if not data_records:
            return

        # 全面改用小寫欄位寫入
        query = """
            INSERT INTO daily_price 
            (ticker, date, open, high, low, close, volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                volume=excluded.volume
        """
        try:
            for record in data_records:
                self.db.execute(query, record)
            self.db.commit()
        except Exception as e:
            logging.error(f"MarketRepository 寫入失敗: {e}")
            self.db.rollback()
            raise e

# ==========================================================
# 實例化全域單例
# ==========================================================
market_repo = MarketRepository()
