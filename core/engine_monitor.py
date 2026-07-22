# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.2.0 (Phase 5: 台美股獨立報價引擎)
#
# 📋 進版說明 (Version Notes):
#   1. [核心重構] 徹底分離台股與美股的 yf.download 請求，防止時差與休市導致的 NaN 空值互相干擾，修復美股無法讀取問題。
#   2. [效能維持] 依舊保持批次下載優勢。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻報價與資料解析模組 (分流機制)
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
# 2️⃣ 高頻報價與資料解析模組 (分流機制)
# ==========================================================
def fetch_realtime_quotes(tickers):
    """分離台美股下載，防止 Pandas 互相干擾導致 NaN 誤刪"""
    quotes = {}
    if not tickers:
        return quotes
        
    tw_tickers = [t for t in tickers if '.TW' in t or t == '^TWII']
    us_tickers = [t for t in tickers if '.TW' not in t and t != '^TWII']
    
    def process_download(group_tickers):
        if not group_tickers: return
        try:
            data = yf.download(group_tickers, period="5d", progress=False, threads=True)
            if data.empty: return
            is_multi = isinstance(data.columns, pd.MultiIndex)
            
            for ticker in group_tickers:
                try:
                    if is_multi:
                        if 'Close' in data and ticker in data['Close']:
                            close_series = data['Close'][ticker].dropna()
                            open_series = data['Open'][ticker].dropna()
                        else: continue
                    else:
                        close_series = data['Close'].dropna()
                        open_series = data['Open'].dropna()

                    if len(close_series) >= 2:
                        curr = float(close_series.iloc[-1])
                        prev = float(close_series.iloc[-2])
                        open_p = float(open_series.iloc[-1])
                        
                        change_amt = curr - prev
                        change_pct = (change_amt / prev * 100) if prev > 0 else 0.0
                        
                        quotes[ticker] = {
                            'current': round(curr, 2),
                            'prev': round(prev, 2),
                            'open': round(open_p, 2),
                            'change_amt': round(change_amt, 2),
                            'change_pct': round(change_pct, 2)
                        }
                except Exception as inner_e:
                    pass
        except Exception as e:
            pass

    # 分別執行，互不干擾
    process_download(tw_tickers)
    process_download(us_tickers)
    
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
