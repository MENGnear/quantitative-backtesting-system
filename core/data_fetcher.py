# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/data_fetcher.py
# 程式版本 : fetcher_v1.4.0 (Phase 7: 智慧同步與增量抓取版)
#
# 📋 進版說明 (Version Notes):
#   1. [智慧跳過] 新增 is_up_to_date 判斷。比對資料庫最新日期與現實時間，若已是最新則直接跳過不發送請求。
#   2. [增量抓取] 若資料庫已有舊資料但未更新，改抓 period="1mo" 補齊；完全無資料才抓 "5y"。
#   3. [Fail-Fast] 延續快速失敗與即時轉播機制。
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import yfinance as yf
import pandas as pd
import logging
import time
import random
from datetime import datetime, timedelta
from core.repositories.market_repository import market_repo

def get_tw_current_date():
    """取得台灣時區的現在日期 (UTC+8)"""
    return (datetime.utcnow() + timedelta(hours=8)).date()

def is_up_to_date(last_date_str):
    """
    智慧判斷資料庫的日期是否已是最新 (支援週末與週一自動推算)。
    :param last_date_str: 資料庫中最新的一筆日期字串 (YYYY-MM-DD)
    """
    if not last_date_str:
        return False
        
    try:
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        today = get_tw_current_date()
        
        days_diff = (today - last_date).days
        weekday = today.weekday() # 0=Mon, 5=Sat, 6=Sun
        
        # 依照今天是星期幾，容許不同的時間差 (如六日一，允許誤差到上週五)
        if weekday == 5:   # 星期六
            expected_diff = 1 # 容許到星期五
        elif weekday == 6: # 星期日
            expected_diff = 2 # 容許到星期五
        elif weekday == 0: # 星期一
            expected_diff = 3 # 若尚未收盤，容許到星期五
        else:
            expected_diff = 1 # 平日容許到昨天
            
        return days_diff <= expected_diff
    except Exception as e:
        logging.error(f"日期解析錯誤: {e}")
        return False

def smart_update_historical_data(tickers, force_5y=False, progress_bar=None, status_text=None):
    """
    智慧更新 K 線資料 (具備防 Ban、增量抓取、智慧跳過與即時 UI 廣播機制)
    回傳: (is_all_success: bool, failed_tickers: list)
    """
    failed_tickers = []
    total_tickers = len(tickers)
    
    for idx, ticker in enumerate(tickers):
        success = False
        current_step = idx + 1
        
        # 🔍 Step 1: 檢查資料庫最新庫存日期
        last_date_str = market_repo.get_last_date(ticker)
        
        if is_up_to_date(last_date_str):
            skip_msg = f"⏭️ [{current_step}/{total_tickers}] {ticker} 庫存已是最新 ({last_date_str})，略過抓取。"
            logging.info(skip_msg)
            if status_text: status_text.info(skip_msg)
            time.sleep(0.3) # 短暫停留視覺
            if progress_bar: progress_bar.progress(current_step / total_tickers)
            continue
            
        # 決定抓取範圍：若已建檔但舊了，就抓 1 個月補齊；若完全沒建檔，才抓 5 年
        fetch_period = "5y" if not last_date_str else "1mo"
        
        # 🔍 Step 2: 執行抓取 (最多重試 2 次)
        for attempt in range(2):
            try:
                msg = f"⏳ [{current_step}/{total_tickers}] 準備抓取 {ticker} ({fetch_period}) ... (第 {attempt+1}/2 次嘗試)"
                logging.info(msg)
                if status_text: status_text.info(msg)
                
                df = yf.Ticker(ticker).history(period=fetch_period)
                
                if df.empty:
                    raise ValueError("取得空資料")
                    
                df.reset_index(inplace=True)
                
                records = []
                for _, row in df.iterrows():
                    date_str = row['Date'].strftime('%Y-%m-%d')
                    records.append((ticker, date_str, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
                
                # 寫入資料庫
                market_repo.upsert_historical_data(records)
                success = True
                
                success_msg = f"✅ [{current_step}/{total_tickers}] {ticker} 更新成功！(防Ban冷卻中...)"
                logging.info(success_msg)
                if status_text: status_text.success(success_msg)
                
                # 成功後，隨機休息 1.5~3 秒
                time.sleep(random.uniform(1.5, 3.0))
                break 
                
            except Exception as e:
                err_msg = f"⚠️ [{ticker}] 抓取失敗: {e}"
                logging.warning(err_msg)
                
                if attempt < 1:
                    wait_msg = f"🛑 {ticker} 遭阻擋，等待 5 秒後重新嘗試..."
                    if status_text: status_text.warning(wait_msg)
                    logging.info(wait_msg)
                    time.sleep(5)
                    
        # 若失敗則寫入失敗名單
        if not success:
            fail_msg = f"❌ [{ticker}] 連續失敗，已標記為抓取異常，換下一檔。"
            logging.error(fail_msg)
            if status_text: status_text.error(fail_msg)
            failed_tickers.append(ticker)
            time.sleep(2.0) 
            
        if progress_bar:
            progress_bar.progress(current_step / total_tickers)
            
    is_all_success = len(failed_tickers) == 0
    return is_all_success, failed_tickers
