# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/db_manager.py
# 程式版本 : core_v2.0.0 (Phase 2: 雙軌制資料庫重構)
#
# 📋 進版說明 (Version Notes):
#   1. [重構] 廢棄 user_watchlist，正式拆分為 monitor_pool (頁面 A) 與 backtest_pool (頁面 B)。
#   2. [擴充] 針對兩張新資料表，分別撰寫專屬的 CRUD (新增、讀取、刪除) 功能。
#   3. [維持] 保留 daily_price K線資料表，以及智慧獲取中文名稱的爬蟲功能。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 資料庫與資料表初始化 (Table Creation)
#   - 2️⃣ 智慧命名爬蟲 (Name Fetcher)
#   - 3️⃣ 頁面 A：Monitor Pool 專屬 CRUD
#   - 4️⃣ 頁面 B：Backtest Pool 專屬 CRUD
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import os
import requests
from bs4 import BeautifulSoup
import logging

# 設定 Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 使用絕對路徑錨定 database 資料夾
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# ==========================================================
# 1️⃣ 資料庫與資料表初始化 (Table Creation)
# ==========================================================
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # [頁面 A] 實戰監測池：包含門檻與警報價位
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitor_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                market TEXT,
                threshold_pct TEXT,
                entry_price TEXT,
                exit_price TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # [頁面 B] 策略回測池：僅需代碼作為回測母體
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                market TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # [歷史資料] K線存放區 (維持不變)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_price (
                ticker TEXT NOT NULL,
                Date TEXT NOT NULL,
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume INTEGER,
                PRIMARY KEY (ticker, Date)
            )
        ''')
        conn.commit()
    logging.info("✅ QBS 雙軌制資料庫初始化完成！(monitor_pool, backtest_pool, daily_price)")

# ==========================================================
# 2️⃣ 智慧命名爬蟲 (Name Fetcher)
# ==========================================================
def fetch_stock_name(ticker, market):
    """透過 Yahoo Finance 爬取股票乾淨中文/英文名稱"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://finance.yahoo.com/quote/{ticker}"
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('h1')
            if title_tag:
                raw_title = title_tag.text.strip()
                clean_name = raw_title.split('(')[0].strip()
                
                if market == 'tw':
                    clean_name = clean_name.replace(".TW", "").replace(".TWO", "")
                    if " " in clean_name:
                        parts = clean_name.split(" ", 1)
                        if parts[0].isdigit():
                            return f"{parts[0]} {parts[1]}"
                return clean_name
                
        return ticker 
    except Exception as e:
        logging.error(f"抓取名稱失敗 ({ticker}): {e}")
        return ticker

# ==========================================================
# 3️⃣ 頁面 A：Monitor Pool 專屬 CRUD
# ==========================================================
def add_monitor_item(ticker, market="tw", thresholds="", entry_prices="", exit_prices=""):
    """新增股票至頁面 A 實戰監測池"""
    ticker = ticker.strip().upper()
    display_name = fetch_stock_name(ticker, market)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO monitor_pool (ticker, display_name, market, threshold_pct, entry_price, exit_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ticker, display_name, market, thresholds, entry_prices, exit_prices))
            conn.commit()
            return True, display_name
        except sqlite3.IntegrityError:
            logging.warning(f"⚠️ {ticker} 已經存在於監測池中。")
            return False, display_name

def remove_monitor_item(ticker):
    """從頁面 A 監測池移除股票"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM monitor_pool WHERE ticker = ?", (ticker,))
        conn.commit()

def get_all_monitor_items():
    """取得頁面 A 所有監測清單"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, display_name, market, threshold_pct, entry_price, exit_price FROM monitor_pool")
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "ticker": row[0],
                "display_name": row[1],
                "market": row[2],
                "threshold_pct": row[3],
                "entry_price": row[4],
                "exit_price": row[5]
            })
        return result

# ==========================================================
# 4️⃣ 頁面 B：Backtest Pool 專屬 CRUD
# ==========================================================
def add_backtest_item(ticker, market="tw"):
    """新增股票至頁面 B 策略回測池"""
    ticker = ticker.strip().upper()
    display_name = fetch_stock_name(ticker, market)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO backtest_pool (ticker, display_name, market)
                VALUES (?, ?, ?)
            ''', (ticker, display_name, market))
            conn.commit()
            return True, display_name
        except sqlite3.IntegrityError:
            logging.warning(f"⚠️ {ticker} 已經存在於回測池中。")
            return False, display_name

def remove_backtest_item(ticker):
    """從頁面 B 回測池移除股票"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM backtest_pool WHERE ticker = ?", (ticker,))
        conn.commit()

def get_all_backtest_items():
    """取得頁面 B 所有回測母體清單"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ticker, display_name, market FROM backtest_pool")
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "ticker": row[0],
                "display_name": row[1],
                "market": row[2]
            })
        return result
