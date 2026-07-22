# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.4.0 (Phase 5: MON 併發多線程極速版)
#
# 📋 進版說明 (Version Notes):
#   1. [效能解放] 導入 concurrent.futures 多線程技術，台美股報價同步併發，解決美股單線程排隊卡頓問題。
#   2. [精準數值] 確保每檔股票獨立調用 fast_info 的 last_price 與 previous_close，數值 100% 精準。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻報價與資料解析模組 (🔥 V1.4.0 併發多線程引擎)
#   - 3️⃣ 警報觸發與冷卻邏輯
#   - 4️⃣ 引擎主程序
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import pandas as pd
import yfinance as yf
import datetime
import os
import logging
import concurrent.futures

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# ==========================================================
# 1️⃣ 基礎環境與冷卻記憶體初始化
# ==========================================================
COOLDOWN_SECONDS = 900 
_ALERT_HISTORY = {}

def get_monitor_targets():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM monitor_pool", conn)

# ==========================================================
# 2️⃣ 高頻報價與資料解析模組 (🔥 V1.4.0 併發多線程引擎)
# ==========================================================
def fetch_single_quote(ticker):
    """獨立執行緒的單一標的報價抓取，確保無陣列偏移"""
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        
        curr = float(fi.last_price)
        prev = float(fi.previous_close)
        
        try:
            open_p = float(fi.open)
        except Exception:
            open_p = prev # 若無開盤價則以昨收代替
            
        change_amt = curr - prev
        change_pct = (change_amt / prev * 100) if prev > 0 else 0.0
        
        return ticker, {
            'current': round(curr, 2),
            'prev': round(prev, 2),
            'open': round(open_p, 2),
            'change_amt': round(change_amt, 2),
            'change_pct': round(change_pct, 2)
        }
    except Exception:
        return ticker, None

def fetch_realtime_quotes(tickers):
    """完全繼承 MON 極速精神：併發多線程 (ThreadPoolExecutor) 處理"""
    quotes = {}
    if not tickers:
        return quotes
        
    # 同時開啟最多 10 條執行緒，瞬間同步發送請求
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(fetch_single_quote, ticker): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker, data = future.result()
            if data:
                quotes[ticker] = data
                
    return quotes

def parse_custom_values(val_str):
    if not val_str or pd.isna(val_str):
        return []
    try:
        return [float(x.strip()) for x in str(val_str).split(',') if x.strip()]
    except Exception:
        return []

# ==========================================================
# 3️⃣ 警報觸發與冷卻邏輯
# ==========================================================
def check_cooldown(alert_key):
    now = datetime.datetime.now().timestamp()
    last_trigger = _ALERT_HISTORY.get(alert_key, 0)
    if (now - last_trigger) > COOLDOWN_SECONDS:
        _ALERT_HISTORY[alert_key] = now
        return True
    return False

def evaluate_alerts(row, quote):
    ticker = row['ticker']
    current_price = quote['current']
    change_pct = quote['change_pct']
    
    alerts = []
    thresholds = parse_custom_values(row['thresholds'])
    entry_prices = parse_custom_values(row['entry_prices'])
    exit_prices = parse_custom_values(row['exit_prices'])

    for th in thresholds:
        if abs(change_pct) >= th:
            direction = "📈 暴漲" if change_pct > 0 else "📉 暴跌"
            alert_key = f"{ticker}_TH_{th}_{direction}"
            if check_cooldown(alert_key):
                alerts.append({'ticker': ticker, 'type': f'波動提醒', 'message': f"今日漲跌幅達 {change_pct}% (達標 {th}%)"})

    for entry in entry_prices:
        if current_price <= entry:
            alert_key = f"{ticker}_ENTRY_{entry}"
            if check_cooldown(alert_key):
                alerts.append({'ticker': ticker, 'type': '🎯 進場', 'message': f"現價達進場設定 ${entry}"})

    for exit_p in exit_prices:
        if current_price >= exit_p:
            alert_key = f"{ticker}_EXIT_{exit_p}"
            if check_cooldown(alert_key):
                alerts.append({'ticker': ticker, 'type': '💰 出場', 'message': f"現價達出場設定 ${exit_p}"})

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序
# ==========================================================
def run_radar_scan():
    targets_df = get_monitor_targets()
    if targets_df.empty:
        return {}, []

    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    for _, row in targets_df.iterrows():
        if row['ticker'] in quotes:
            triggered = evaluate_alerts(row, quotes[row['ticker']])
            all_triggered_alerts.extend(triggered)
            
    return quotes, all_triggered_alerts
