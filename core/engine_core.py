# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.5.0 (Phase 5: MON 原版批次極速引擎)
#
# 📋 進版說明 (Version Notes):
#   1. [架構回歸] 完全回歸 MON 批次併發架構，使用 yf.download(threads=True) 瞬間打包台美股，根除美股排隊卡頓問題。
#   2. [空值過濾] 針對每一檔股票單獨執行 .dropna()，完美避開台美股時差造成的 NaN 錯位，確保漲跌幅計算 100% 精準。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻報價與資料解析模組 (🔥 V1.5.0 批次併發架構)
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
# 2️⃣ 高頻報價與資料解析模組 (🔥 V1.5.0 批次併發架構)
# ==========================================================
def fetch_realtime_quotes(tickers):
    """回歸 MON 的智慧：一次打包，多線程併發下載，絕不卡死"""
    quotes = {}
    if not tickers:
        return quotes
        
    try:
        # 使用 yfinance 底層優化過的多執行緒批次下載
        data = yf.download(tickers, period="5d", progress=False, threads=True)
        if data.empty:
            return quotes
            
        is_multi = isinstance(data.columns, pd.MultiIndex)
        
        for ticker in tickers:
            try:
                # 單獨抽離每檔股票，並執行 dropna() 清除時差產生的 NaN
                if is_multi:
                    if 'Close' in data and ticker in data['Close']:
                        close_s = data['Close'][ticker].dropna()
                        open_s = data['Open'][ticker].dropna()
                    else:
                        continue
                else:
                    close_s = data['Close'].dropna()
                    open_s = data['Open'].dropna()

                # 確保至少有兩天有效資料來計算漲跌
                if len(close_s) >= 2:
                    curr = float(close_s.iloc[-1])
                    prev = float(close_s.iloc[-2])
                    open_p = float(open_s.iloc[-1])
                    
                    change_amt = curr - prev
                    change_pct = (change_amt / prev * 100) if prev > 0 else 0.0
                    
                    quotes[ticker] = {
                        'current': round(curr, 2),
                        'prev': round(prev, 2),
                        'open': round(open_p, 2),
                        'change_amt': round(change_amt, 2),
                        'change_pct': round(change_pct, 2)
                    }
            except Exception:
                pass
    except Exception:
        pass
        
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
