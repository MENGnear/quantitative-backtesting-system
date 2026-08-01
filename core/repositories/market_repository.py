# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.1.2 (Phase 7: 雲端語法相容升級版)
#
# 📋 進版說明 (Version Notes):
#   1. [語法升級] 將 SQLite 專屬的 INSERT OR REPLACE 改為標準的 ON CONFLICT DO UPDATE。
#   2. [欄位防護] SQL 查詢欄位全面加上雙引號 ("Date", "Open"...) 確保大小寫相容。
#   3. [職責轉移] 移除 _ensure_table_exists，建表職責已統一交由 SchemaManager 處理。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組與資料庫連線
#   - 2️⃣ K 線資料讀取介面 (Query)
#   - 3️⃣ K 線資料寫入介面 (Command)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

# ==========================================================
# 1️⃣ 模組與資料庫連線
# ==========================================================
import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        # 取得連線時，ConnectionFactory 已經會自動呼叫 SchemaManager 處理建表
        self.db = ConnectionFactory.get_connection()

# ==========================================================
# 2️⃣ K 線資料讀取介面 (Query)
# ==========================================================
    def get_last_date(self, ticker: str) -> Optional[str]:
        """查詢資料庫中該標的最新的一筆 K 線日期"""
        # 加上雙引號確保欄位大小寫正確
        query = 'SELECT MAX("Date") as last_date FROM daily_price WHERE ticker = ?'
        try:
            result = self.db.fetch_one(query, (ticker,))
            return result['last_date'] if result and result['last_date'] else None
        except Exception:
            return None

    def get_historical_data_df(self, ticker: str) -> pd.DataFrame:
        """提取指定股票的歷史 K 線，並回傳 DataFrame"""
        # 加上雙引號，確保由 Postgres 回傳的字典 Key 維持首字母大寫
        query = 'SELECT "Date", "Open", "High", "Low", "Close", "Volume" FROM daily_price WHERE ticker = ? ORDER BY "Date" ASC'
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
# 3️⃣ K 線資料寫入介面 (Command)
# ==========================================================
    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        """批次寫入或更新 K 線資料 (相容 Postgres 的 ON CONFLICT 語法)"""
        if not data_records:
            return

        # 🔥 修正：替換掉 SQLite 專用的 INSERT OR REPLACE，改用標準 SQL
        query = """
            INSERT INTO daily_price 
            (ticker, "Date", "Open", "High", "Low", "Close", "Volume") 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, "Date") DO UPDATE SET
                "Open"=excluded."Open",
                "High"=excluded."High",
                "Low"=excluded."Low",
                "Close"=excluded."Close",
                "Volume"=excluded."Volume"
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
