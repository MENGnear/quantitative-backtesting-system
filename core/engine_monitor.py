# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.0.0 (Phase 4: 即時雷達警報引擎)
#
# 📋 進版說明 (Version Notes):
#   1. [高頻] 實作 yfinance 極速報價獲取，免抓長天期歷史 K 線。
#   2. [觸發] 支援「自訂漲跌幅門檻 (%)」、「進場價」、「出場價」三維度警報。
#   3. [防護] 內建 Memory Cache 冷卻系統 (Cooldown)，防止盤中價格震盪導致警報連發。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻報價與資料解析模組
#   - 3️⃣ 警報觸發與冷卻邏輯
#   - 4️⃣ 引擎主程序 (雷達掃描)
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
# 警報冷卻時間設定 (秒) - 實戰建議設為 900 (15分鐘) 或 3600 (1小時)
COOLDOWN_SECONDS = 900 
# 記憶體快取：記錄 { '股票代碼_警報類型_數值': 觸發時間戳記 }
_ALERT_HISTORY = {}

def get_monitor_targets():
    """從資料庫獲取實戰監測池清單與自訂門檻"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM monitor_pool", conn)

# ==========================================================
# 2️⃣ 高頻報價與資料解析模組
# ==========================================================
def fetch_realtime_quotes(tickers):
    """極速獲取最新收盤價與昨收價，用於計算即時漲跌幅"""
    quotes = {}
    for ticker in tickers:
        try:
            # 只取近 5 天資料確保能抓到昨收與現價
            df = yf.Ticker(ticker).history(period="5d")
            if len(df) >= 2:
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                quotes[ticker] = {
                    'current': round(current_price, 2),
                    'prev': round(prev_price, 2),
                    'change_pct': round(change_pct, 2)
                }
        except Exception as e:
            logging.error(f"獲取 {ticker} 報價失敗: {e}")
    return quotes

def parse_custom_values(val_str):
    """解析使用者輸入的自訂數值字串 (例如: '5, 10' -> [5.0, 10.0])"""
    if not val_str or pd.isna(val_str):
        return []
    try:
        # 去除空白並以逗號切割，轉換為浮點數陣列
        return [float(x.strip()) for x in str(val_str).split(',') if x.strip()]
    except Exception:
        return []

# ==========================================================
# 3️⃣ 警報觸發與冷卻邏輯
# ==========================================================
def check_cooldown(alert_key):
    """檢查該警報是否在冷卻期內，若通過則更新時間戳記"""
    now = datetime.datetime.now().timestamp()
    last_trigger = _ALERT_HISTORY.get(alert_key, 0)
    
    if (now - last_trigger) > COOLDOWN_SECONDS:
        _ALERT_HISTORY[alert_key] = now
        return True
    return False

def evaluate_alerts(row, quote):
    """評估單一股票是否觸發警報"""
    ticker = row['ticker']
    name = row['display_name']
    current_price = quote['current']
    change_pct = quote['change_pct']
    
    alerts = []
    
    # 解析自訂門檻參數
    thresholds = parse_custom_values(row['thresholds'])
    entry_prices = parse_custom_values(row['entry_prices'])
    exit_prices = parse_custom_values(row['exit_prices'])

    # 1. 檢查漲跌幅門檻 (使用者自訂 %)
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

    # 2. 檢查逢低進場價 (<= 設定值)
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

    # 3. 檢查停利出場價 (>= 設定值)
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
    """執行一次完整的雷達掃描，回傳觸發的警報清單"""
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
    # 終端機獨立測試區塊
    print("📡 啟動即時雷達引擎掃描...")
    alerts = run_radar_scan()
    if alerts:
        print(f"\n🚨 發現 {len(alerts)} 筆觸發警報！")
        for a in alerts:
            print(f"[{a['type']}] {a['name']}({a['ticker']}): {a['message']}")
    else:
        print("\n✅ 掃描完畢，目前無標的觸發設定門檻。")
