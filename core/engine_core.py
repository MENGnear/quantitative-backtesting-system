# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.3.0 (Phase 5: MON 輕量極速精準版)
#
# 📋 進版說明 (Version Notes):
#   1. [效能狂飆] 徹底棄用 yf.download 歷史陣列，改採 MON 原始的 yf.Ticker(sym).fast_info 瞬間快取。
#   2. [數學精準] 直接抓取系統 previous_close 與 last_price，終結漲跌幅計算錯誤 (如跌 10 變漲 90) 漏洞。
#   3. [防護] 確保美股與台股皆能以毫秒級速度獨立回傳。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻極速報價引擎 (🔥 V1.3.0 核心：fast_info 瞬間快照)
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
# 2️⃣ 高頻極速報價引擎 (🔥 V1.3.0 核心)
# ==========================================================
def fetch_realtime_quotes(tickers):
    """
    完全參照 MON 的輕量化做法：
    使用 fast_info 獲取當下瞬間切片，不下載歷史 K 線，確保毫秒級速度與絕對精準。
    """
    quotes = {}
    if not tickers:
        return quotes
        
    for ticker in tickers:
        try:
            # 針對大盤與個股抓取瞬間快照
            tkr = yf.Ticker(ticker)
            fi = tkr.fast_info
            
            # 精準獲取：當下現價 (last_price) 與 官方昨收 (previous_close)
            curr = fi.get('lastPrice') or fi.get('last_price')
            prev = fi.get('previousClose') or fi.get('previous_close')
            open_p = fi.get('open')
            
            if curr is not None and prev is not None:
                curr = float(curr)
                prev = float(prev)
                open_p = float(open_p) if open_p is not None else prev
                
                # 絕對精準的漲跌數學計算
                change_amt = curr - prev
                change_pct = (change_amt / prev * 100) if prev > 0 else 0.0
                
                quotes[ticker] = {
                    'current': round(curr, 2),
                    'prev': round(prev, 2),
                    'open': round(open_p, 2),
                    'change_amt': round(change_amt, 2),
                    'change_pct': round(change_pct, 2)
                }
        except Exception as e:
            pass # 單檔失敗不影響全局
            
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
                alerts.append({'ticker': ticker, 'type': f'波動提醒', 'message': f"漲跌達 {change_pct}% (門檻 {th}%)"})

    for entry in entry_prices:
        if current_price <= entry:
            alert_key = f"{ticker}_ENTRY_{entry}"
            if check_cooldown(alert_key):
                alerts.append({'ticker': ticker, 'type': '🎯 進場', 'message': f"達進場價 ${entry}"})

    for exit_p in exit_prices:
        if current_price >= exit_p:
            alert_key = f"{ticker}_EXIT_{exit_p}"
            if check_cooldown(alert_key):
                alerts.append({'ticker': ticker, 'type': '💰 出場', 'message': f"達出場價 ${exit_p}"})

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序
# ==========================================================
def run_radar_scan():
    targets_df = get_monitor_targets()
    if targets_df.empty:
        return {}, []

    tickers = targets_df['ticker'].tolist()
    
    # 這裡的報價獲取現在是毫秒級的
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    for _, row in targets_df.iterrows():
        if row['ticker'] in quotes:
            triggered = evaluate_alerts(row, quotes[row['ticker']])
            all_triggered_alerts.extend(triggered)
            
    return quotes, all_triggered_alerts
