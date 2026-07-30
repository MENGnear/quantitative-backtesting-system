# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/connection_factory.py
# 程式版本 : db_layer_v1.0.0 (Pre-Phase 7: Step 2 - Factory)
#
# 📋 進版說明 (Version Notes):
#   1. [單例模式] 實作 ConnectionFactory，確保全域共用唯一的 Adapter 實例。
#   2. [動態路由] 預留環境變數判斷，未來可無縫切換至 PostgresAdapter。
# ==========================================================

import os
from .base import DatabaseAdapter
from .sqlite_adapter import SQLiteAdapter

class ConnectionFactory:
    _instance: DatabaseAdapter = None

    @classmethod
    def get_connection(cls) -> DatabaseAdapter:
        """
        獲取全域唯一的資料庫轉接器實例 (Singleton)
        """
        if cls._instance is None:
            # 動態定位資料庫路徑 (對齊根目錄的 database/stock_system.db)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, "database", "stock_system.db")
            
            # TODO: 未來可在此加入 config 判斷 (若 env == 'production' 則回傳 PostgresAdapter)
            # 目前預設回傳 SQLiteAdapter
            cls._instance = SQLiteAdapter(db_path)
            
        return cls._instance
