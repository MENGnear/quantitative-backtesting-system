# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.1.0 (Phase 4: 報價模組強固版)
#
# 📋 進版說明 (Version Notes):
#   1. [修復] 將 yfinance 報價獲取區間由 5d 擴展為 1mo，避免連假導致無昨收價可算的問題。
#   2. [優化] 強制轉換數值型別 (float)，避免 Pandas Series 結構導致 UI 渲染卡死。
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
# 2️⃣ 高頻報價與資料解析模組 (🔥 V1.1.0 修復區塊)
# ==========================================================
def fetch_realtime_quotes(tickers):
    """極速獲取最新收盤價與昨收價，並計算漲跌幅"""
    quotes = {}
    for ticker in tickers:
        try:
            # 擴大範圍至 1 個月，確保無論如何都能抓到至少 2 個交易日
            df = yf.Ticker(ticker).history(period="1mo")
            
            if not df.empty and len(df) >= 2:
                # 強制轉為 float，避免 Pandas 格式污染
                current_price = float(df['Close'].iloc[-1])
                prev_price = float(df['Close'].iloc[-2])
                
                # 計算漲跌幅
                if prev_price > 0:
                    change_pct = ((current_price - prev_price) / prev_price) * 100
                else:
                    change_pct = 0.0
                    
                quotes[ticker] = {
                    'current': round(current_price, 2),
                    'prev': round(prev_price, 2),
                    'change_pct': round(change_pct, 2)
                }
            else:
                logging.warning(f"⚠️ [{ticker}] 歷史資料不足 2 天，無法計算報價與漲跌幅。")
        except Exception as e:
            logging.error(f"❌ 獲取 [{ticker}] 報價失敗: {e}")
            
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
        return []

    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        if ticker in quotes:
            triggered = evaluate_alerts(row, quotes[ticker])
            all_triggered_alerts.extend(triggered)
            
    return all_triggered_alerts

if __name__ == "__main__":
    print("📡 啟動即時雷達引擎掃描...")
    alerts = run_radar_scan()
    if alerts:
        print(f"\n🚨 發現 {len(alerts)} 筆觸發警報！")
        for a in alerts:
            print(f"[{a['type']}] {a['name']}({a['ticker']}): {a['message']}")
    else:
        print("\n✅ 掃描完畢，目前無標的觸發設定門檻。")
