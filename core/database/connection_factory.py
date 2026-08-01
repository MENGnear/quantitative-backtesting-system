# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/connection_factory.py
# 程式版本 : v1.3.0 (Phase 7: 雲端/地端雙軌模式 + 自動建表)
#
# 📋 進版說明 (Version Notes):
#   1. [架構升級] 導入 Streamlit Secrets 偵測機制。
#   2. [自動切換] 偵測到 DATABASE_URL 時自動指派 PostgresAdapter，否則退回 SQLiteAdapter。
#   3. [防呆機制] 整合 SchemaManager，連線成功後自動執行 `initialize_database` 初始化空資料庫。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與依賴
#   - 2️⃣ 連線工廠主程式 (Singleton Pattern)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

# ==========================================================
# 1️⃣ 模組匯入與依賴
# ==========================================================
import os
import streamlit as st
import logging
from core.database.sqlite_adapter import SQLiteAdapter
from core.database.postgres_adapter import PostgresAdapter
from core.database.schema_manager import SchemaManager

# ==========================================================
# 2️⃣ 連線工廠主程式 (Singleton Pattern)
# ==========================================================
class ConnectionFactory:
    """資料庫連線工廠：負責依據環境配置，分派正確的 Database Adapter，並自動初始化資料表"""
    _db_instance = None

    @classmethod
    def get_connection(cls):
        """
        獲取資料庫連線實例 (單例模式)
        邏輯：
        1. 檢查是否已有連線實例。
        2. 若無，則依據 Streamlit Secrets 決定連線至雲端 Postgres 或本地 SQLite。
        3. 建立連線後，自動呼叫 SchemaManager 確保所有必要的 Table 都已存在。
        """
        if cls._db_instance is None:
            db_url = None
            
            # 1. 嘗試從 Streamlit Secrets 獲取雲端資料庫連線字串
            try:
                if "DATABASE_URL" in st.secrets:
                    db_url = st.secrets["DATABASE_URL"]
            except Exception:
                pass
            
            # 2. 根據環境分配對應的 Adapter
            if db_url:
                logging.info("🌍 偵測到 DATABASE_URL 金鑰，系統將連線至雲端 PostgreSQL。")
                cls._db_instance = PostgresAdapter(db_url)
            else:
                logging.info("🏠 未偵測到雲端設定，系統將退回使用本機 SQLite。")
                
                # 確保地端資料庫存放目錄存在
                db_path = os.path.join("database", "stock_system.db")
                os.makedirs("database", exist_ok=True)
                
                cls._db_instance = SQLiteAdapter(db_path)
            
            # 3. 🛡️ 【關鍵新增】啟動防呆機制：連線後立刻自動檢查並建立缺少的資料表
            if cls._db_instance is not None:
                SchemaManager.initialize_database(cls._db_instance)
                
        return cls._db_instance
