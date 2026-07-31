# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/market_repository.py
# 程式版本 : repo_v1.0.0 (Pre-Phase 7: 市場 K 線資料倉儲)
#
# 📋 進版說明 (Version Notes):
#   1. [領域隔離] 負責處理 daily_price 資料表的所有進出。
#   2. [依賴反轉] 拔除 sqlite3，改由 ConnectionFactory 調用底層。
# ==========================================================

import pandas as pd
from typing import List, Tuple, Optional
from core.database.connection_factory import ConnectionFactory
import logging

class MarketRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()

    def get_last_date(self, ticker: str) -> Optional[str]:
        """查詢資料庫中該標的最新的一筆 K 線日期"""
        query = "SELECT MAX(Date) as last_date FROM daily_price WHERE ticker = ?"
        result = self.db.fetch_one(query, (ticker,))
        return result['last_date'] if result and result['last_date'] else None

    def upsert_historical_data(self, data_records: List[Tuple]) -> None:
        """
        批次寫入或更新 K 線資料 (INSERT OR REPLACE)
        data_records 格式必須為: (ticker, Date, Open, High, Low, Close, Volume)
        """
        if not data_records:
            return

        query = """
            INSERT OR REPLACE INTO daily_price 
            (ticker, Date, Open, High, Low, Close, Volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        # 注意：我們目前的 Adapter 的 execute 尚未實作 executemany，
        # 所以這裡先用迴圈執行，或者未來我們可以在 base.py 擴充 executemany。
        # 為了保證目前的穩定性，我們在此封裝內部迴圈並統一 commit。
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

# ==========================================================
# 實例化全域單例
# ==========================================================
market_repo = MarketRepository()
