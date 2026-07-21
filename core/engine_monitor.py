# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.1.2 (Phase 4: 批次多線程防卡死版)
#
# 📋 進版說明 (Version Notes):
#   1. [核心修復] 捨棄 Ticker 迴圈，改用 yf.download 批次多線程下載，大幅提升速度並避免單一標的卡死。
#   2. [容錯處理] 自動適配 yfinance 單檔/多檔回傳結構，過濾無效代碼。
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
# 2️⃣ 高頻報價與資料解析模組 (🔥 V1.1.2 全新改寫)
# ==========================================================
def fetch_realtime_quotes(tickers):
    """使用批次下載，徹底解決迴圈卡死與連線掛起問題"""
    quotes = {}
    if not tickers:
        return quotes
        
    try:
        # 使用 yf.download 批次抓取近 7 天資料，關閉終端機進度條干擾
        data = yf.download(tickers, period="7d", progress=False, threads=True)
        if data.empty:
            return quotes
            
        # 判定回傳的是單檔(SingleIndex)還是多檔(MultiIndex)
        is_multi = isinstance(data.columns, pd.MultiIndex)
        
        for ticker in tickers:
            try:
                if is_multi:
                    # 檢查該 ticker 是否在資料中
                    if 'Close' in data and ticker in data['Close']:
                        series = data['Close'][ticker].dropna()
                    else:
                        continue
                else:
                    series = data['Close'].dropna()

                if len(series) >= 2:
                    curr = float(series.iloc[-1])
                    prev = float(series.iloc[-2])
                    change_pct = ((curr - prev) / prev * 100) if prev > 0 else 0.0
                    
                    quotes[ticker] = {
                        'current': round(curr, 2),
                        'prev': round(prev, 2),
                        'change_pct': round(change_pct, 2)
                    }
            except Exception as inner_e:
                logging.warning(f"⚠️ 解析 [{ticker}] 報價失敗: {inner_e}")
                
    except Exception as e:
        logging.error(f"❌ 批次獲取報價發生嚴重錯誤: {e}")
        
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
    name = row['display_name']
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
                alerts.append({
                    'ticker': ticker,
                    'name': name,
                    'type': f'波動提醒 ({direction})',
                    'message': f"現價 ${current_price}，今日漲跌幅達 {change_pct}% (觸發自訂 {th}% 門檻)"
                })

    for entry in entry_prices:
        if current_price <= entry:
            alert_key = f"{ticker}_ENTRY_{entry}"
            if check_cooldown(alert_key):
                alerts.append({
                    'ticker': ticker,
                    'name': name,
                    'type': '🎯 進場提醒',
                    'message': f"現價 ${current_price} 已跌至/低於您設定的進場價 ${entry}"
                })

    for exit_p in exit_prices:
        if current_price >= exit_p:
            alert_key = f"{ticker}_EXIT_{exit_p}"
            if check_cooldown(alert_key):
                alerts.append({
                    'ticker': ticker,
                    'name': name,
                    'type': '💰 出場提醒',
                    'message': f"現價 ${current_price} 已達/突破您設定的出場價 ${exit_p}"
                })

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序 (雷達掃描)
# ==========================================================
def run_radar_scan():
    targets_df = get_monitor_targets()
    if targets_df.empty:
        return {}, []

    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        if ticker in quotes:
            triggered = evaluate_alerts(row, quotes[ticker])
            all_triggered_alerts.extend(triggered)
            
    return quotes, all_triggered_alerts

if __name__ == "__main__":
    print("📡 啟動即時雷達引擎掃描...")
    quotes, alerts = run_radar_scan()
    if alerts:
        print(f"\n🚨 發現 {len(alerts)} 筆觸發警報！")
        for a in alerts:
            print(f"[{a['type']}] {a['name']}({a['ticker']}): {a['message']}")
    else:
        print("\n✅ 掃描完畢，目前無標的觸發設定門檻。")
