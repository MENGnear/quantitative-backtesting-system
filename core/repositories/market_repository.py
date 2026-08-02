# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.4.0 (Phase 7: 雲端字典永久化與時序鎖定版)
#
# 📋 進版說明 (Version Notes):
#   1. [字典上雲] 新增 stock_dictionary 資料表，永久儲存查詢過的股票代碼與名稱。
#   2. [自動建表] 導入 Lazy Initialization (_ensure_dict_table)，無痛自動建立資料表。
#   3. [時序鎖定] 延續 K 線資料讀取時的 df.sort_index()，確保分數絕不亂跳。
# ==========================================================

import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()
        self._dict_initialized = False

    # ==========================================================
    # 📌 雲端股票字典管理 (單一事實來源)
    # ==========================================================
    def _ensure_dict_table(self):
        """Lazy 初始化：確保雲端字典資料表存在"""
        if not self._dict_initialized:
            query = """
                CREATE TABLE IF NOT EXISTS stock_dictionary (
                    ticker VARCHAR(50) PRIMARY KEY,
                    display_name VARCHAR(100),
                    market VARCHAR(10)
                )
            """
            try:
                self.db.execute(query)
                self.db.commit()
                self._dict_initialized = True
            except Exception as e:
                self.db.rollback()
                logging.error(f"無法建立 stock_dictionary 資料表: {e}")

    def upsert_dict_item(self, ticker: str, display_name: str, market: str) -> None:
        """寫入或更新股票字典 (永久儲存)"""
        self._ensure_dict_table()
        query = """
            INSERT INTO stock_dictionary (ticker, display_name, market)
            VALUES (?, ?, ?)
            ON CONFLICT (ticker) DO UPDATE SET
                display_name = excluded.display_name,
                market = excluded.market
        """
        try:
            self.db.execute(query, (ticker, display_name, market))
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logging.error(f"寫入 stock_dictionary 失敗: {e}")

    def get_dict_options(self, market: str) -> list:
        """讀取指定市場的所有股票字典紀錄"""
        self._ensure_dict_table()
        query = "SELECT ticker, display_name FROM stock_dictionary WHERE market = ? ORDER BY ticker ASC"
        try:
            rows = self.db.fetch_all(query, (market,))
            return rows if rows else []
        except Exception as e:
            logging.error(f"讀取 stock_dictionary 失敗: {e}")
            return []

    # ==========================================================
    # 📌 K 線歷史資料管理
    # ==========================================================
    def get_last_date(self, ticker: str) -> Optional[str]:
        query = "SELECT MAX(date) as last_date FROM daily_price WHERE ticker = ?"
        try:
            result = self.db.fetch_one(query, (ticker,))
            return result['last_date'] if result and result['last_date'] else None
        except Exception:
            return None

    def get_historical_data_df(self, ticker: str) -> pd.DataFrame:
        query = "SELECT date, open, high, low, close, volume FROM daily_price WHERE ticker = ? ORDER BY date ASC"
        try:
            rows = self.db.fetch_all(query, (ticker,))
            if not rows:
                return pd.DataFrame()
                
            df = pd.DataFrame(rows)
            df.rename(columns={
                'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
            }, inplace=True)
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            df.dropna(inplace=True)
            
            # 🔒 關鍵修復：強制時間序列定序，徹底消滅分數亂跳 Bug
            df.sort_index(ascending=True, inplace=True)
            return df
        except Exception as e:
            logging.warning(f"讀取 {ticker} K 線資料失敗: {e}")
            return pd.DataFrame()

    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        if not data_records:
            return
        query = """
            INSERT INTO daily_price (ticker, date, open, high, low, close, volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close, volume=excluded.volume
        """
        try:
            for record in data_records:
                self.db.execute(query, record)
            self.db.commit()
        except Exception as e:
            logging.error(f"MarketRepository 寫入失敗: {e}")
            self.db.rollback()
            raise e

market_repo = MarketRepository()
