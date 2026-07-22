# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/db_manager.py
# 程式版本 : db_v2.2.0 (Phase 5: 完美整合 MON 自動清洗機制)
#
# 📋 進版說明 (Version Notes):
#   1. [架構升級] 導入 Auto-Heal 自動清洗機制，啟動時自動掃描並移除資料庫中的奇摩髒標籤。
#   2. [穩定性] 確保過往新增的無效名稱自動修正，無須手動刪除 DB 檔案。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與路徑設定
#   - 2️⃣ 資料庫初始化與自動清洗 (Auto-Heal)
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
# 2️⃣ 資料庫初始化與自動清洗 (Auto-Heal)
# ==========================================================
def init_db():
    """初始化資料庫，並執行 MON 自動清洗防護"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 建立資料表
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_pool (
                ticker TEXT PRIMARY KEY,
                display_name TEXT,
                market TEXT
            )
        ''')
        
        # 🔥 Auto-Heal：自動清洗過往寫入的髒資料
        clean_targets = ["(.TW) 走勢圖", "(TW) 走勢圖", " - Yahoo奇摩股市"]
        for dirty_str in clean_targets:
            cursor.execute(f"UPDATE monitor_pool SET display_name = REPLACE(display_name, '{dirty_str}', '')")
            cursor.execute(f"UPDATE backtest_pool SET display_name = REPLACE(display_name, '{dirty_str}', '')")
            
        conn.commit()

# ==========================================================
# 3️⃣ 實戰監測池 (Monitor Pool) 存取邏輯
# ==========================================================
def get_all_monitor_items():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM monitor_pool").fetchall()]

def add_monitor_item(ticker, display_name=None, market="tw", thresholds="", entry_prices="", exit_prices=""):
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
