# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/schema_manager.py
# 程式版本 : v1.2.0 (Phase 7: 補齊 K 線資料表)
#
# 📋 進版說明 (Version Notes):
#   1. [新增結構] 加入 daily_price 資料表的 DDL 定義，支援雲端 K 線儲存。
#   2. [相容防護] 針對 Date, Open 等欄位名稱加上雙引號 ("")，防止 PostgreSQL 自動轉小寫，
#                確保與上層 Pandas DataFrame 的欄位名稱 (大小寫) 完全相容。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入
#   - 2️⃣ 建表語法定義區 (DDL)
#   - 3️⃣ 初始化執行邏輯
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

# ==========================================================
# 1️⃣ 模組匯入
# ==========================================================
import logging

class SchemaManager:
    """
    資料庫綱要管理員：
    負責在系統啟動與連線資料庫時，自動檢查並建立所需的資料表結構。
    """

# ==========================================================
# 2️⃣ 建表語法定義區 (DDL)
# ==========================================================
    # 從 monitor_repository 提取的 monitor_pool 資料表結構
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
    
    # 從 strategy_repository 提取的 backtest_pool 資料表結構
    CREATE_BACKTEST_POOL_TABLE = """
        CREATE TABLE IF NOT EXISTS backtest_pool (
            ticker VARCHAR(50) PRIMARY KEY,
            display_name VARCHAR(255),
            market VARCHAR(50)
        );
    """

    # 從 market_repository 提取的 daily_price (K線) 資料表結構
    # 使用雙引號確保大小寫不被資料庫引擎改變，相容舊有 Pandas 邏輯
    CREATE_DAILY_PRICE_TABLE = """
        CREATE TABLE IF NOT EXISTS daily_price (
            ticker VARCHAR(50),
            "Date" VARCHAR(50),
            "Open" REAL,
            "High" REAL,
            "Low" REAL,
            "Close" REAL,
            "Volume" REAL,
            PRIMARY KEY (ticker, "Date")
        );
    """

# ==========================================================
# 3️⃣ 初始化執行邏輯
# ==========================================================
    @classmethod
    def initialize_database(cls, db_adapter):
        """
        執行所有建表語法。
        :param db_adapter: 當前的 Database Adapter 實例 (Postgres 或 SQLite)
        """
        try:
            logging.info("⚙️ 開始檢查並初始化資料庫資料表結構...")
            
            # 依序執行所有建表指令
            db_adapter.execute(cls.CREATE_MONITOR_POOL_TABLE)
            db_adapter.execute(cls.CREATE_BACKTEST_POOL_TABLE)
            db_adapter.execute(cls.CREATE_DAILY_PRICE_TABLE)
            
            # 提交交易
            db_adapter.commit()
            
            logging.info("✅ 資料庫資料表結構初始化完成！")
        except Exception as e:
            logging.error(f"❌ 資料庫初始化失敗: {e}")
            # 若發生錯誤，回滾交易確保資料庫不崩潰
            db_adapter.rollback()
