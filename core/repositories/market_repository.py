# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.1.0 (Phase 7: 自動建表與讀取封裝)
# ==========================================================

import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """防呆機制：確保 daily_price 資料表存在"""
        query = """
            CREATE TABLE IF NOT EXISTS daily_price (
                ticker TEXT,
                Date TEXT,
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume REAL,
                PRIMARY KEY (ticker, Date)
            )
        """
        try:
            self.db.execute(query)
            self.db.commit()
        except Exception as e:
            logging.error(f"MarketRepository 初始化資料表失敗: {e}")

    def get_last_date(self, ticker: str) -> Optional[str]:
        """查詢資料庫中該標的最新的一筆 K 線日期"""
        query = "SELECT MAX(Date) as last_date FROM daily_price WHERE ticker = ?"
        try:
            result = self.db.fetch_one(query, (ticker,))
            return result['last_date'] if result and result['last_date'] else None
        except Exception:
            return None

    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        """批次寫入或更新 K 線資料 (INSERT OR REPLACE)"""
        if not data_records:
            return

        query = """
            INSERT OR REPLACE INTO daily_price 
            (ticker, Date, Open, High, Low, Close, Volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.db.connect()
        cursor = self.db.conn.cursor()
        try:
            cursor.executemany(query, data_records)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logging.error(f"MarketRepository 寫入失敗: {e}")
            raise e
        finally:
            cursor.close()

    def get_historical_data_df(self, ticker: str) -> pd.DataFrame:
        """提取指定股票的歷史 K 線，並回傳 DataFrame"""
        query = "SELECT Date, Open, High, Low, Close, Volume FROM daily_price WHERE ticker = ? ORDER BY Date ASC"
        try:
            rows = self.db.fetch_all(query, (ticker,))
            if not rows:
                return pd.DataFrame()
                
            df = pd.DataFrame(rows)
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
# 實例化全域單例
# ==========================================================
market_repo = MarketRepository()
