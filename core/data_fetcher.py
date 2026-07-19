# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/data_fetcher.py
# 程式版本 : core_v1.0.0 (Phase 2: 智慧增量下載與防封鎖模組)
#
# 📋 進版說明 (Version Notes):
#   1. [新增] 實作 get_safe_session()，加入 User-Agent 偽裝與自動重試機制，防止 Yahoo 封鎖。
#   2. [核心] 實作 smart_update_historical_data()，先查詢 SQLite 取得最新日期，計算缺口後動態決定下載 5y 還是 6mo。
#   3. [優化] 使用 INSERT OR REPLACE 進行 SQLite 寫入，確保資料 100% 縫合連續且無重複。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與防封鎖設定 (Imports & Session)
#   - 2️⃣ 資料庫日期查詢 (DB Date Check)
#   - 3️⃣ 智慧增量下載與寫入核心 (Smart Fetch & Upsert)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import yfinance as yf
import pandas as pd
import sqlite3
import datetime
import time
import random
import logging
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

# 絕對路徑對齊 db_manager
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# 設定 Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================================
# 1️⃣ 模組匯入與防封鎖設定 (Anti-Ban Session)
# ==========================================================
def get_safe_session():
    """建立帶有偽裝標頭與自動重試機制的 Requests Session"""
    session = Session()
    # 隨機挑選常見的瀏覽器 User-Agent 進行偽裝
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ]
    session.headers.update({
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    
    # 設定重試機制 (遇到 429 或 50X 錯誤時自動重試 3 次)
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session

# ==========================================================
# 2️⃣ 資料庫日期查詢 (Check Database Gap)
# ==========================================================
def get_last_date(ticker):
    """查詢資料庫中該標的最新的一筆 K 線日期"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(Date) FROM daily_price WHERE ticker = ?", (ticker,))
            result = cursor.fetchone()
            return result[0] if result[0] else None
    except Exception as e:
        logging.error(f"查詢 {ticker} 最新日期失敗: {e}")
        return None

# ==========================================================
# 3️⃣ 智慧增量下載與寫入核心 (Smart Fetch & Upsert)
# ==========================================================
def smart_update_historical_data(tickers=None, force_5y=False):
    """
    智慧增量更新 K 線資料
    - tickers: 股票代碼 List。若為 None，則自動從資料庫讀取全部關注清單。
    - force_5y: 強制更新過去 5 年資料 (供 UI 上的強制按鈕使用)
    """
    # 如果沒有提供 tickers，自動去 user_watchlist 把所有代碼撈出來
    if not tickers:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ticker FROM user_watchlist")
                tickers = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"讀取監測清單失敗: {e}")
            return False

    if not tickers:
        logging.warning("⚠️ 沒有任何標的需要更新。")
        return True

    session = get_safe_session()
    today = datetime.date.today()
    updated_count = 0

    for ticker in tickers:
        try:
            # 1. 決定下載區間 (Period)
            fetch_period = "6mo" # 預設抓半年進行縫合
            
            if force_5y:
                fetch_period = "5y"
            else:
                last_date_str = get_last_date(ticker)
                if not last_date_str:
                    fetch_period = "5y" # 全新股票，抓 5 年
                    logging.info(f"[{ticker}] 全新標的，準備下載 5 年歷史資料...")
                else:
                    last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
                    gap_days = (today - last_date).days
                    
                    if gap_days > 180:
                        fetch_period = "5y" # 斷層大於半年，保險起見直接重抓 5 年
                        logging.info(f"[{ticker}] 資料斷層過大 ({gap_days}天)，準備下載 5 年歷史資料...")
                    else:
                        fetch_period = "6mo" # 斷層小於半年，抓半年進行重疊縫合
                        logging.info(f"[{ticker}] 增量更新模式 (缺口 {gap_days}天)，下載 6 個月資料進行縫合...")

            # 2. 透過 yfinance 下載資料
            stock = yf.Ticker(ticker, session=session)
            hist = stock.history(period=fetch_period)
            
            if hist.empty:
                logging.warning(f"[{ticker}] ⚠️ 無法抓取到任何資料，請確認代碼是否正確。")
                continue
                
            # 3. 整理 DataFrame 格式
            hist.reset_index(inplace=True)
            # 統一日期格式為 YYYY-MM-DD
            hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
            # 挑選我們需要的欄位
            records = hist[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            # 加入 ticker 欄位作為主鍵的一部分
            records['ticker'] = ticker
            
            # 轉換為 List of Tuples，準備寫入 SQLite
            # 順序對應: ticker, Date, Open, High, Low, Close, Volume
            data_to_insert = list(records[['ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].itertuples(index=False, name=None))
            
            # 4. 寫入 SQLite (使用 INSERT OR REPLACE 進行完美重疊縫合)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR REPLACE INTO daily_price 
                    (ticker, Date, Open, High, Low, Close, Volume) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', data_to_insert)
                conn.commit()
            
            updated_count += 1
            logging.info(f"[{ticker}] ✅ 成功更新 {len(data_to_insert)} 筆 K 線資料。")
            
            # 5. 人性化隨機延遲 (防止封鎖的核心)
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logging.error(f"[{ticker}] 更新失敗: {e}")
            continue

    logging.info(f"🎉 批次更新結束！共成功更新 {updated_count}/{len(tickers)} 檔標的。")
    return True

# ----------------------------------------------------------
# 單元測試 (本機開發測試用)
# ----------------------------------------------------------
if __name__ == "__main__":
    print("🚀 測試啟動：智慧增量下載器")
    # 測試單檔更新 (可嘗試先跑一次，再跑第二次看 Gap 邏輯)
    smart_update_historical_data(["2330.TW", "AAPL"])
