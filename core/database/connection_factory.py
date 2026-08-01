# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/connection_factory.py
# 程式版本 : v1.2.0 (Phase 7: 雲端/地端雙軌模式)
#
# 📋 進版說明 (Version Notes):
#   1. [架構升級] 導入 Streamlit Secrets 偵測機制。
#   2. [自動切換] 偵測到 DATABASE_URL 時自動指派 PostgresAdapter，否則退回 SQLiteAdapter。
#   3. [相容保留] 完整保留原有地端 SQLite 連線邏輯。
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

# ==========================================================
# 2️⃣ 連線工廠主程式 (Singleton Pattern)
# ==========================================================
class ConnectionFactory:
    """資料庫連線工廠：負責依據環境配置，分派正確的 Database Adapter"""
    _db_instance = None

    @classmethod
    def get_connection(cls):
        """
        獲取資料庫連線實例 (單例模式)
        邏輯：
        1. 若 Streamlit Secrets 中存在 DATABASE_URL (雲端環境)，則回傳 PostgresAdapter。
        2. 若不存在 (地端開發環境)，則自動建立 database 資料夾，並回傳 SQLiteAdapter。
        """
        if cls._db_instance is None:
            db_url = None
            
            # 1. 嘗試從 Streamlit Secrets 獲取雲端資料庫連線字串
            try:
                # 這裡使用 dict 檢查方式，避免直接呼叫引發 KeyError
                if "DATABASE_URL" in st.secrets:
                    db_url = st.secrets["DATABASE_URL"]
            except Exception:
                # 若未在 Streamlit 環境中執行，會捕捉異常並忽略
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
                
        return cls._db_instance
