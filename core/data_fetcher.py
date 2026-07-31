# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/data_fetcher.py
# 程式版本 : core_v1.1.0 (Pre-Phase 7: 倉儲層對接版)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 徹底拔除 sqlite3，所有資料庫讀寫改由 market_repo 與 strategy_repo 處理。
#   2. [核心保留] 100% 保留 v1.0.0 的 User-Agent 防封鎖與智慧增量邏輯 (5y/6mo 判斷)。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與防封鎖設定 (Imports & Session)
#   - 2️⃣ 智慧增量下載與寫入核心 (Smart Fetch & Upsert)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import yfinance as yf
import pandas as pd
import datetime
import time
import random
import logging
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 🔥 引入新架構的倉儲層
from core.repositories.market_repository import market_repo
from core.repositories.strategy_repository import strategy_repo

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
# 2️⃣ 智慧增量下載與寫入核心 (Smart Fetch & Upsert)
# ==========================================================
def smart_update_historical_data(tickers=None, force_5y=False):
    """
    智慧增量更新 K 線資料
    - tickers: 股票代碼 List。若為 None，則自動從回測倉儲取得所有標的。
    - force_5y: 強制更新過去 5 年資料 (供 UI 上的強制按鈕使用)
    """
    # 如果沒有提供 tickers，改由 strategy_repo 取得全庫標的
    if not tickers:
        try:
            items = strategy_repo.get_all_backtest_items()
            tickers = [item['ticker'] for item in items]
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
                # 🔥 改由 market_repo 查詢最新日期
                last_date_str = market_repo.get_last_date(ticker)
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
            
            # 4. 寫入 SQLite (交由倉儲層處理)
            market_repo.upsert_historical_data(data_to_insert)
            
            updated_count += 1
            logging.info(f"[{ticker}] ✅ 成功更新 {len(data_to_insert)} 筆 K 線資料。")
            
            # 5. 人性化隨機延遲 (防止封鎖的核心)
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logging.error(f"[{ticker}] 更新失敗: {e}")
            continue

    logging.info(f"🎉 批次更新結束！共成功更新 {updated_count}/{len(tickers)} 檔標的。")
    return True
