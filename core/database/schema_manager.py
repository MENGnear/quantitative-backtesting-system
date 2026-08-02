# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/schema_manager.py
# 程式版本 : v1.3.0 (Phase 7: PostgreSQL 全小寫相容版)
#
# 📋 進版說明 (Version Notes):
#   1. [架構統一] 將 daily_price 的欄位全面改為小寫 (date, open, high...)。
#   2. [防錯機制] 徹底避免 PostgreSQL 自動轉換大小寫導致的 column does not exist 錯誤。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入
#   - 2️⃣ 建表語法定義區 (DDL)
#   - 3️⃣ 初始化執行邏輯
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import logging

class SchemaManager:
    """資料庫綱要管理員：負責在系統啟動與連線資料庫時，自動檢查並建立所需的資料表結構。"""

    CREATE_MONITOR_POOL_TABLE = """
        CREATE TABLE IF NOT EXISTS monitor_pool (
            ticker VARCHAR(50) PRIMARY KEY,
            display_name VARCHAR(255),
            market VARCHAR(50),
            thresholds TEXT,
            entry_prices TEXT,
            exit_prices TEXT
        );
    """
    
    CREATE_BACKTEST_POOL_TABLE = """
        CREATE TABLE IF NOT EXISTS backtest_pool (
            ticker VARCHAR(50) PRIMARY KEY,
            display_name VARCHAR(255),
            market VARCHAR(50)
        );
    """

    # 🔥 關鍵修正：全面改為小寫欄位
    CREATE_DAILY_PRICE_TABLE = """
        CREATE TABLE IF NOT EXISTS daily_price (
            ticker VARCHAR(50),
            date VARCHAR(50),
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (ticker, date)
        );
    """

    @classmethod
    def initialize_database(cls, db_adapter):
        try:
            logging.info("⚙️ 開始檢查並初始化資料庫資料表結構...")
            db_adapter.execute(cls.CREATE_MONITOR_POOL_TABLE)
            db_adapter.execute(cls.CREATE_BACKTEST_POOL_TABLE)
            db_adapter.execute(cls.CREATE_DAILY_PRICE_TABLE)
            db_adapter.commit()
            logging.info("✅ 資料庫資料表結構初始化完成！")
        except Exception as e:
            logging.error(f"❌ 資料庫初始化失敗: {e}")
            db_adapter.rollback()
