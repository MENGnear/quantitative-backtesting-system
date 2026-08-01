# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/schema_manager.py
# 程式版本 : v1.0.0 (Phase 7: 雲端建表自動化)
#
# 📋 進版說明 (Version Notes):
#   1. [全新建立] 實作資料庫綱要管理員 (Schema Manager)。
#   2. [自動初始化] 統一存放 DDL (CREATE TABLE) 語法，解決雲端資料庫初始為空的問題。
#   3. [相容設計] 使用 IF NOT EXISTS，確保每次連線重新整理時不會重複建表報錯。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入
#   - 2️⃣ 建表語法定義區
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
    
    # 未來若有 strategy 或其他資料表，可接續新增在此處
    # CREATE_STRATEGY_TABLE = """ ... """

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
            
            # 依序執行建表指令
            db_adapter.execute(cls.CREATE_MONITOR_POOL_TABLE)
            
            # 提交交易
            db_adapter.commit()
            
            logging.info("✅ 資料庫資料表結構初始化完成！")
        except Exception as e:
            logging.error(f"❌ 資料庫初始化失敗: {e}")
            # 若發生錯誤，回滾交易確保資料庫不崩潰
            db_adapter.rollback()
