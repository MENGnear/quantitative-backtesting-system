# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.3.1 (Phase 7: 絕對時序鎖定版)
#
# 📋 進版說明 (Version Notes):
#   1. [時序鎖定] 在 K 線資料載入 DataFrame 後，強制執行 df.sort_index()。
#   2. [Bug 修復] 徹底根除因多執行緒與資料庫字串排序誤差，導致 Pandas 計算均線與 RSI 產生分數跳動的問題。
# ==========================================================

import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()

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
            
            # 🔒 關鍵修復：強制時間序列定序，剝奪 SQL 排序主導權，徹底消滅分數亂跳 Bug
            df.sort_index(ascending=True, inplace=True)
            
            return df
        except Exception as e:
            logging.warning(f"讀取 {ticker} K 線資料失敗 (可能尚未下載或鎖定): {e}")
            return pd.DataFrame()

    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        if not data_records:
            return

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

market_repo = MarketRepository()
