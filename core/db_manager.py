# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/db_manager.py
# 程式版本 : db_v2.1.0 (Phase 4.1: 支援警報門檻欄位擴充)
#
# 📋 進版說明 (Version Notes):
#   1. [Schema 更新] 在 monitor_pool 新增 thresholds, entry_prices, exit_prices 欄位。
#   2. [寫入支援] add_monitor_item 函式支援接收與寫入上述三個警報參數。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與路徑設定
#   - 2️⃣ 資料庫與資料表初始化 (init_db)
#   - 3️⃣ 實戰監測池 (Monitor Pool) 存取邏輯
#   - 4️⃣ 策略回測池 (Backtest Pool) 存取邏輯
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import os

# ==========================================================
# 1️⃣ 基礎環境與路徑設定
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# ==========================================================
# 2️⃣ 資料庫與資料表初始化 (init_db)
# ==========================================================
def init_db():
    """初始化資料庫與資料表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 🌟 實戰監測池 (加入 Phase 4 的警報欄位)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitor_pool (
                ticker TEXT PRIMARY KEY,
                display_name TEXT,
                market TEXT,
                thresholds TEXT,
                entry_prices TEXT,
                exit_prices TEXT
            )
        ''')
        
        # 🌟 策略回測池
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_pool (
                ticker TEXT PRIMARY KEY,
                display_name TEXT,
                market TEXT
            )
        ''')
        conn.commit()

# ==========================================================
# 3️⃣ 實戰監測池 (Monitor Pool) 存取邏輯
# ==========================================================
def get_all_monitor_items():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM monitor_pool").fetchall()]

def add_monitor_item(ticker, display_name=None, market="tw", thresholds="", entry_prices="", exit_prices=""):
    """將標的與警報設定寫入監測池"""
    if not display_name:
        display_name = ticker
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO monitor_pool 
            (ticker, display_name, market, thresholds, entry_prices, exit_prices) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticker, display_name, market, thresholds, entry_prices, exit_prices))
        conn.commit()

def remove_monitor_item(ticker):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM monitor_pool WHERE ticker = ?", (ticker,))
        conn.commit()

# ==========================================================
# 4️⃣ 策略回測池 (Backtest Pool) 存取邏輯
# ==========================================================
def get_all_backtest_items():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM backtest_pool").fetchall()]

def add_backtest_item(ticker, display_name=None, market="tw"):
    if not display_name:
        display_name = ticker
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT OR REPLACE INTO backtest_pool 
            (ticker, display_name, market) 
            VALUES (?, ?, ?)
        ''', (ticker, display_name, market))
        conn.commit()

def remove_backtest_item(ticker):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM backtest_pool WHERE ticker = ?", (ticker,))
        conn.commit()
