# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/db_manager.py
# 程式版本 : core_v1.0.0 (Phase 2: 資料層基礎建設)
#
# 📋 進版說明 (Version Notes):
#   1. [新增] 建立 QBS 專案的資料庫統一管理模組 (Database Manager)。
#   2. [建置] 實作 init_db()，初始化 user_watchlist, daily_price, tw50_signals 三大資料表。
#   3. [功能] 提供針對 user_watchlist 的 CRUD 操作 (新增、查詢、刪除)，供前端 UI 安全呼叫。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與路徑設定 (Imports & Paths)
#   - 2️⃣ 資料庫初始化 (Database Initialization)
#   - 3️⃣ 監測清單管理功能 (Watchlist CRUD Operations)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import os
import logging

# ==========================================================
# 1️⃣ 模組匯入與路徑設定
# ==========================================================
# 絕對路徑解析：確保資料庫永遠建立在專案根目錄的 database/ 資料夾下
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "stock_system.db")

# 確保 database 資料夾存在，若無則自動建立
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# ==========================================================
# 2️⃣ 資料庫初始化
# ==========================================================
def init_db():
    """初始化系統所需的資料表 (若已存在則不影響原有資料)"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Table 1: 永久監測清單 (取代舊版 Session 與 JSON 暫存)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_watchlist (
                    ticker TEXT PRIMARY KEY,
                    display_name TEXT,
                    market TEXT,
                    thresholds TEXT,
                    entry_prices TEXT,
                    exit_prices TEXT
                )
            ''')
            
            # Table 2: 5 年歷史 K 線資料 (重型讀寫庫)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_price (
                    ticker TEXT, 
                    Date TEXT, 
                    Open REAL, 
                    High REAL, 
                    Low REAL, 
                    Close REAL, 
                    Volume INTEGER,
                    PRIMARY KEY (ticker, Date)
                )
            ''')
            
            # Table 3: TW50 回測訊號與評分 (輕量庫，專供 UI 極速渲染)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tw50_signals (
                    ticker TEXT PRIMARY KEY,
                    update_time TEXT,
                    close REAL,
                    high REAL,
                    score INTEGER,
                    s1 INTEGER, s2 INTEGER, s3 INTEGER, s4 INTEGER, s5 INTEGER,
                    rsi_6 REAL, rsi_14 REAL, rsi_24 REAL,
                    atr REAL, stop_tgt REAL, risk_pct REAL
                )
            ''')
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"資料庫初始化失敗: {e}")
        return False

# ==========================================================
# 3️⃣ 監測清單管理功能 (Watchlist CRUD Operations)
# ==========================================================
def add_watchlist_item(ticker, display_name, market, thresholds="", entry_prices="", exit_prices=""):
    """
    新增或更新監測標的 (UI 側邊欄呼叫)
    若 ticker 已存在，則透過 REPLACE 覆蓋更新設定。
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_watchlist 
                (ticker, display_name, market, thresholds, entry_prices, exit_prices)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ticker, display_name, market, thresholds, entry_prices, exit_prices))
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"新增監測標的失敗 ({ticker}): {e}")
        return False

def remove_watchlist_item(ticker):
    """移除指定的監測標的 (UI 側邊欄呼叫)"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_watchlist WHERE ticker = ?", (ticker,))
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"移除監測標的失敗 ({ticker}): {e}")
        return False

def get_all_watchlist():
    """
    取得所有監測清單
    回傳值：List of Dictionaries，方便 Streamlit 前端直接讀取與操作。
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # 讓回傳結果可以直接用 dict 的 key 存取
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_watchlist ORDER BY ticker ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"讀取監測清單失敗: {e}")
        return []

# ----------------------------------------------------------
# 單元測試與初始化觸發
# ----------------------------------------------------------
if __name__ == "__main__":
    print(f"📂 資料庫路徑解析結果: {DB_PATH}")
    if init_db():
        print("✅ SQLite 資料庫與資料表初始化成功！")
    else:
        print("❌ SQLite 資料庫初始化失敗！")
