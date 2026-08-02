# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/data_fetcher.py
# 程式版本 : fetcher_v1.2.0 (Phase 7: 流量管制與退避重試版)
#
# 📋 進版說明 (Version Notes):
#   1. [防鎖機制] 加入隨機延遲 1~3 秒 (Rate Limiting)，偽裝人類操作避免 429 錯誤。
#   2. [退避重試] 若遭遇失敗，等待 30 秒後重新抓取，最多重試 3 次 (Exponential Backoff)。
#   3. [狀態回報] 函數改為回傳 (是否全數成功, 失敗股票名單)，供前端進行 UI 防呆渲染。
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import yfinance as yf
import pandas as pd
import logging
import time
import random
from core.repositories.market_repository import market_repo

def smart_update_historical_data(tickers, force_5y=False):
    """
    智慧更新 K 線資料 (具備防 Ban 與 30 秒重試機制)
    回傳: (is_all_success: bool, failed_tickers: list)
    """
    failed_tickers = []
    
    for ticker in tickers:
        success = False
        
        # 最多重試 3 次
        for attempt in range(3):
            try:
                period = "5y" if force_5y else "1y"
                logging.info(f"⏳ 準備抓取 {ticker} ({period}) ... (第 {attempt+1}/3 次嘗試)")
                
                df = yf.Ticker(ticker).history(period=period)
                
                if df.empty:
                    raise ValueError("取得空資料")
                    
                df.reset_index(inplace=True)
                
                records = []
                for _, row in df.iterrows():
                    # 統一將 datetime 轉為字串格式存入資料庫
                    date_str = row['Date'].strftime('%Y-%m-%d')
                    records.append((ticker, date_str, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
                
                # 寫入資料庫
                market_repo.upsert_historical_data(records)
                success = True
                
                logging.info(f"✅ [{ticker}] 更新成功！")
                
                # 成功後，隨機休息 1~3 秒以迴避 Yahoo 偵測
                time.sleep(random.uniform(1.0, 3.0))
                break # 成功則跳出重試迴圈
                
            except Exception as e:
                logging.warning(f"⚠️ [{ticker}] 抓取失敗: {e}")
                if attempt < 2: # 若還沒到最後一次，則等待 30 秒
                    logging.info(f"💤 進入退避冷卻，等待 30 秒後重試...")
                    time.sleep(30)
                    
        # 3 次都失敗，將該檔股票登記到失敗清單
        if not success:
            logging.error(f"❌ [{ticker}] 三次重試皆失敗，放棄該標的。")
            failed_tickers.append(ticker)
            
    is_all_success = len(failed_tickers) == 0
    return is_all_success, failed_tickers
