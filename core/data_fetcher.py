# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/data_fetcher.py
# 程式版本 : fetcher_v1.3.0 (Phase 7: 即時戰況轉播與快速失敗版)
#
# 📋 進版說明 (Version Notes):
#   1. [Fail-Fast] 降低重試次數為 2 次，失敗冷卻時間縮短為 5 秒，避免網頁假死。
#   2. [UI 聯動] 支援接收 Streamlit 的 progress_bar 與 status_text，即時廣播進度。
#   3. [視覺停留] 刻意在顯示狀態文字後加入延遲 (Sleep)，解決文字閃現無法閱讀的問題。
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import yfinance as yf
import pandas as pd
import logging
import time
import random
from core.repositories.market_repository import market_repo

def smart_update_historical_data(tickers, force_5y=False, progress_bar=None, status_text=None):
    """
    智慧更新 K 線資料 (具備防 Ban、5 秒快速失敗與即時 UI 廣播機制)
    回傳: (is_all_success: bool, failed_tickers: list)
    """
    failed_tickers = []
    total_tickers = len(tickers)
    
    for idx, ticker in enumerate(tickers):
        success = False
        current_step = idx + 1
        
        # 最多重試 2 次 (Fail-Fast 策略)
        for attempt in range(2):
            try:
                period = "5y" if force_5y else "1y"
                msg = f"⏳ [{current_step}/{total_tickers}] 準備抓取 {ticker} ... (第 {attempt+1}/2 次嘗試)"
                logging.info(msg)
                if status_text: status_text.info(msg)
                
                df = yf.Ticker(ticker).history(period=period)
                
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
                
                # 成功狀態顯示與視覺停留
                success_msg = f"✅ [{current_step}/{total_tickers}] {ticker} 更新成功！(防Ban冷卻中...)"
                logging.info(success_msg)
                if status_text: status_text.success(success_msg)
                
                # 成功後，隨機休息 1.5~3 秒 (兼顧防禦機制與讓使用者能看清楚文字)
                time.sleep(random.uniform(1.5, 3.0))
                break # 成功則跳出重試迴圈
                
            except Exception as e:
                err_msg = f"⚠️ [{ticker}] 抓取失敗: {e}"
                logging.warning(err_msg)
                
                if attempt < 1: # 若還沒到最後一次，則等待 5 秒
                    wait_msg = f"🛑 {ticker} 遭阻擋，等待 5 秒後重新嘗試..."
                    if status_text: status_text.warning(wait_msg)
                    logging.info(wait_msg)
                    time.sleep(5)
                    
        # 2 次都失敗，將該檔股票登記到失敗清單，並停留 2 秒讓使用者看清楚
        if not success:
            fail_msg = f"❌ [{ticker}] 連續失敗，已標記為抓取異常，換下一檔。"
            logging.error(fail_msg)
            if status_text: status_text.error(fail_msg)
            failed_tickers.append(ticker)
            time.sleep(2.0) # 刻意停留，避免閃現
            
        # 更新總進度條
        if progress_bar:
            progress_bar.progress(current_step / total_tickers)
            
    is_all_success = len(failed_tickers) == 0
    return is_all_success, failed_tickers
