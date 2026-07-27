# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.3.3 (Phase 6.5: 接收並執行主開關指令)
#
# 📋 進版說明 (Version Notes):
#   1. [推播升級] 串接 telegram_service，實作自動推播單行極簡格式。
#   2. [防洗機制] 加入警報判定端的時區隔離，確保休市期間的標的不會被誤觸發警報。
#   3. [重大修復] (v1.3.3) 導入 is_monitoring 參數。若未啟動監測，引擎只提供 UI 報價，嚴格封鎖自動推播與警報。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化
#   - 2️⃣ 高頻報價與資料解析模組
#   - 3️⃣ 警報觸發與冷卻邏輯 
#   - 4️⃣ 引擎主程序 (🔥 導入 is_monitoring 阻斷閘門)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import pandas as pd
import yfinance as yf
import datetime
import pytz
import os
import logging
from services.telegram_service import send_telegram_message, build_qbs_tg_msg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# ==========================================================
# 1️⃣ 基礎環境與冷卻記憶體初始化
# ==========================================================
_ALERT_HISTORY = {}

def get_monitor_targets():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM monitor_pool", conn)

# ==========================================================
# 2️⃣ 高頻報價與資料解析模組
# ==========================================================
def fetch_realtime_quotes(tickers):
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
def evaluate_alerts(row, quote, tz_now):
    ticker = row['ticker']
    current_price = quote['current']
    change_pct = quote['change_pct']
    
    clean_name = str(row['display_name']).strip()
    if not clean_name or clean_name == ticker:
        clean_name = ticker.replace('.TW', '')
    
    alerts = []
    thresholds = parse_custom_values(row['thresholds'])
    entry_prices = parse_custom_values(row['entry_prices'])
    exit_prices = parse_custom_values(row['exit_prices'])

    is_triggered = False
    trigger_reasons = []

    for th in thresholds:
        if abs(change_pct) >= th:
            is_triggered = True
            trigger_reasons.append(f"達標 {th}%")
            break

    for entry in entry_prices:
        if current_price >= entry:
            is_triggered = True
            trigger_reasons.append(f"進場達標")
            break

    for exit_p in exit_prices:
        if current_price <= exit_p:
            is_triggered = True
            trigger_reasons.append(f"出場達標")
            break

    if is_triggered:
        reason_str = "及".join(trigger_reasons)
        alerts.append({'ticker': ticker, 'type': '🚨 觸發', 'message': f"{reason_str} (${current_price})"})
        
        current_interval_id = f"{tz_now.strftime('%Y%m%d_%H')}_{(tz_now.minute // 5) * 5:02d}"
        
        if _ALERT_HISTORY.get(ticker) != current_interval_id:
            msg = build_qbs_tg_msg(clean_name, current_price, change_pct, is_manual=False)
            send_telegram_message(msg)
            _ALERT_HISTORY[ticker] = current_interval_id

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序
# ==========================================================
def run_radar_scan(is_monitoring=False):
    targets_df = get_monitor_targets()
    tz_now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    
    is_tw_time = 6 <= tz_now.hour <= 18
    target_idx = '^TWII' if is_tw_time else '^IXIC'
    idx_name = "TW" if is_tw_time else "US"
    
    # 🌟 閘門 1：只有在監測狀態下，才執行大盤 15 分鐘常規廣播
    if is_monitoring:
        idx_interval_id = f"IDX_{tz_now.strftime('%Y%m%d_%H')}_{(tz_now.minute // 15) * 15:02d}"
        if _ALERT_HISTORY.get('INDEX') != idx_interval_id:
            idx_quotes = fetch_realtime_quotes([target_idx])
            if target_idx in idx_quotes:
                q = idx_quotes[target_idx]
                msg = build_qbs_tg_msg(idx_name, q['current'], q['change_pct'], is_manual=False)
                send_telegram_message(msg)
                _ALERT_HISTORY['INDEX'] = idx_interval_id
            
    if targets_df.empty:
        return {}, []

    # 為了維持 UI 全時段顯示，這裡依然抓取所有目標的報價
    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    
    # 🌟 閘門 2：只有在監測狀態下，才去計算並觸發個股警報
    if is_monitoring:
        for _, row in targets_df.iterrows():
            if row['ticker'] in quotes:
                is_tw_stock = '.TW' in row['ticker']
                if (is_tw_time and is_tw_stock) or (not is_tw_time and not is_tw_stock):
                    triggered = evaluate_alerts(row, quotes[row['ticker']], tz_now)
                    all_triggered_alerts.extend(triggered)
            
    return quotes, all_triggered_alerts
