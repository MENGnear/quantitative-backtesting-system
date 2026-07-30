# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/monitor_repository.py
# 程式版本 : repo_v1.0.0 (Pre-Phase 7: Step 3 - Pioneer Repository)
#
# 📋 進版說明 (Version Notes):
#   1. [領域隔離] 將「雷達監控標的」的 CRUD 操作獨立為專屬倉儲，落實單一職責原則 (SRP)。
#   2. [依賴反轉] 拔除 sqlite3，改由 ConnectionFactory 取得 DatabaseAdapter 進行操作。
#   3. [向下相容] 提供 get_monitor_targets_df() 供現有的 engine_monitor.py 無縫介接。
# ==========================================================

import pandas as pd
from core.database.connection_factory import ConnectionFactory

class MonitorRepository:
    def __init__(self):
        # 透過單例工廠，取得目前系統指定的資料庫轉接器 (SQLite 或未來的 Postgres)
        self.db = ConnectionFactory.get_connection()

    def get_all_monitor_items(self) -> list:
        """獲取所有監控標的 (回傳 List[Dict])"""
        query = "SELECT * FROM monitor_targets"
        return self.db.fetch_all(query)

    def get_monitor_targets_df(self) -> pd.DataFrame:
        """
        獲取所有監控標的並轉換為 DataFrame。
        這是為了向下相容現有的 engine_monitor.py 所設計的防護層。
        """
        data = self.get_all_monitor_items()
        if not data:
            # 建立帶有標準欄位的空 DataFrame 防呆
            return pd.DataFrame(columns=[
                'ticker', 'display_name', 'market', 
                'thresholds', 'entry_prices', 'exit_prices'
            ])
        return pd.DataFrame(data)

    def add_monitor_item(self, ticker: str, display_name: str = None, market: str = 'tw', 
                         thresholds: str = None, entry_prices: str = None, exit_prices: str = None) -> None:
        """新增監控標的 (若存在則更新 UPSERT)"""
        if display_name is None:
            display_name = ticker

        query = """
            INSERT INTO monitor_targets (ticker, display_name, market, thresholds, entry_prices, exit_prices)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                display_name=excluded.display_name,
                market=excluded.market,
                thresholds=excluded.thresholds,
                entry_prices=excluded.entry_prices,
                exit_prices=excluded.exit_prices
        """
        params = (ticker, display_name, market, thresholds, entry_prices, exit_prices)
        
        # 透過介面執行並提交交易
        self.db.execute(query, params)
        self.db.commit()

    def remove_monitor_item(self, ticker: str) -> None:
        """刪除指定的監控標的"""
        query = "DELETE FROM monitor_targets WHERE ticker = ?"
        self.db.execute(query, (ticker,))
        self.db.commit()

# ==========================================================
# 實例化全域單例，方便上層應用直接 import 使用
# ==========================================================
monitor_repo = MonitorRepository()
