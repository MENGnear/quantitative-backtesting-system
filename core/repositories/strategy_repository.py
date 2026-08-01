# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/repositories/strategy_repository.py
# 程式版本 : repo_v1.0.1 (Phase 7: 回測策略專屬倉儲)
#
# 📋 進版說明 (Version Notes):
#   1. [領域隔離] 將「回測策略標的」的 CRUD 操作獨立為專屬倉儲。
#   2. [依賴反轉] 徹底拔除 sqlite3，改由 ConnectionFactory 調用底層。
#   3. [修復實例] 確保檔案末端正確宣告 strategy_repo 實例供外部 import。
# ==========================================================

import pandas as pd
from core.database.connection_factory import ConnectionFactory

class StrategyRepository:
    def __init__(self):
        self.db = ConnectionFactory.get_connection()

    def get_all_backtest_items(self) -> list:
        """獲取所有回測標的 (回傳 List[Dict])"""
        query = "SELECT * FROM backtest_pool"
        return self.db.fetch_all(query)

    def get_backtest_targets_df(self) -> pd.DataFrame:
        """獲取所有回測標的並轉換為 DataFrame"""
        data = self.get_all_backtest_items()
        if not data:
            return pd.DataFrame(columns=['ticker', 'display_name', 'market'])
        return pd.DataFrame(data)

    def add_backtest_item(self, ticker: str, market: str = 'tw', display_name: str = None) -> None:
        """新增回測標的 (若存在則忽略或更新)"""
        if display_name is None:
            display_name = ticker

        query = """
            INSERT INTO backtest_pool (ticker, display_name, market)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                display_name=excluded.display_name,
                market=excluded.market
        """
        params = (ticker, display_name, market)
        self.db.execute(query, params)
        self.db.commit()

    def remove_backtest_item(self, ticker: str) -> None:
        """刪除指定的回測標的"""
        query = "DELETE FROM backtest_pool WHERE ticker = ?"
        self.db.execute(query, (ticker,))
        self.db.commit()

# ==========================================================
# 實例化全域單例，方便上層應用直接 import 使用 (請勿刪除此行)
# ==========================================================
strategy_repo = StrategyRepository()
