# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/db_manager.py
# 程式版本 : core_v1.1.0 (Phase 2: 整合 Smart 中文命名與防呆機制)
#
# 📋 進版說明 (Version Notes):
#   1. [新增] 匯入 requests 與 re，實作 fetch_chinese_name 爬取 Yahoo 股市中文名稱。
#   2. [優化] 於 add_watchlist_item 底層納入 .TW 自動補齊防呆機制。
#   3. [優化] 寫入資料庫時，自動將 display_name 轉為乾淨的中文格式 (例: 2330 台積電)。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與路徑設定 (Imports & Paths)
#   - 2️⃣ 資料庫初始化 (Database Initialization)
#   - 3️⃣ 爬蟲與名稱解析 (Web Scraping & Naming) - 🔥 V1.1.0 新增
#   - 4️⃣ 監測清單管理功能 (Watchlist CRUD Operations) - 🔥 V1.1.0 優化
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import os
import logging
import requests
import re

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
            
            # Table 1: 永久監測清單
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
            
            # Table 2: 5 年歷史 K 線資料
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
            
            # Table 3: TW50 回測訊號與評分
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
# 3️⃣ 爬蟲與名稱解析 (Web Scraping & Naming)
# ==========================================================
def fetch_chinese_name(ticker):
    """爬取 Yahoo 股市的中文名稱 (承襲 A_MON 的優良傳統)"""
    display_name = ticker
    if ".TW" in ticker.upper():
        code = ticker.upper().replace(".TW", "")
        try:
            res = requests.get(f"https://tw.stock.yahoo.com/quote/{code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            match = re.search(r'<title>(.*?)\(', res.text)
            if match:
                chinese_name = match.group(1).strip()
                display_name = f"{code} {chinese_name}"
            else:
                display_name = code
        except Exception:
            display_name = code
            
    return display_name.replace(".TW", "")

# ==========================================================
# 4️⃣ 監測清單管理功能 (Watchlist CRUD Operations)
# ==========================================================
def add_watchlist_item(ticker, display_name="", market="", thresholds="", entry_prices="", exit_prices=""):
    """新增或更新監測標的 (具備自動補齊與中文爬蟲功能)"""
    # 1. 防呆邏輯：首字為數字且無 .TW 則自動補齊
    ticker = ticker.strip().upper()
    if ticker[0].isdigit() and ".TW" not in ticker:
        ticker += ".TW"

    # 2. 市場判斷
    if not market:
        market = "tw" if ".TW" in ticker else "us"

    # 3. 智慧中文命名
    if not display_name or display_name == ticker or display_name == ticker.replace(".TW", ""):
        display_name = fetch_chinese_name(ticker)

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
    """移除指定的監測標的"""
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
    """取得所有監測清單"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
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
