# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.4.0 (Phase 7: 市場作息感知與三階段推播管線)
#
# 📋 進版說明 (Version Notes):
#   1. [重大修復] 導入 is_monitoring 參數，若未啟動監測則封鎖自動推播與警報。
#   2. [顯示優化] UI 顯示與推播脫鉤，自動推播強制只顯示純代碼 (例: 00631L)，達成極簡視覺。
#   3. [功能升級] (v1.4.0) 導入狀態機與作息感知。支援 🟢開盤 與 🔴收盤 通知，具備美東夏冬令自動切換。
#   4. [邏輯重構] (v1.4.0) 實作三階段管線，確保收盤當下 (如 13:30) 能先發送最後一筆報價，再發送收盤通知。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與狀態記憶體初始化 (🔥 新增作息狀態機)
#   - 2️⃣ 高頻報價與資料解析模組
#   - 3️⃣ 警報觸發與冷卻邏輯
#   - 4️⃣ 引擎主程序 (🔥 三階段過濾管線)
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
# 1️⃣ 基礎環境與狀態記憶體初始化
# ==========================================================
_ALERT_HISTORY = {}
# 🔥 市場作息狀態記憶體
_MARKET_STATE = {'TW': 'CLOSED', 'US': 'CLOSED'}

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
# 4️⃣ 引擎主程序 (🔥 三階段過濾管線)
# ==========================================================
def run_radar_scan(is_monitoring=False):
    global _MARKET_STATE
    targets_df = get_monitor_targets()
    
    # 建立精確的時區時間 (US/Eastern 自動處理夏/冬令切換)
    now_tpe = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    now_us = now_tpe.astimezone(pytz.timezone('US/Eastern'))
    
    now_tpe_time = now_tpe.time()
    now_us_time = now_us.time()
    
    # 定義精確的開關盤節點
    tw_open = datetime.time(9, 0)
    tw_close_trigger = datetime.time(13, 30)
    tw_close_process = datetime.time(13, 30, 59) # 容許 13:30 當分鐘的最後一筆資料處理
    
    us_open = datetime.time(9, 30)
    us_close_trigger = datetime.time(16, 0)
    us_close_process = datetime.time(16, 0, 59)
    
    process_tw = False
    process_us = False

    # 🌟 階段一：開盤判定與狀態更新
    if is_monitoring:
        if tw_open <= now_tpe_time <= tw_close_process:
            process_tw = True
            if now_tpe_time < tw_close_trigger and _MARKET_STATE.get('TW') != 'OPEN':
                _MARKET_STATE['TW'] = 'OPEN'
                send_telegram_message("🎯TW | 🟢開盤")
                
        if us_open <= now_us_time <= us_close_process:
            process_us = True
            if now_us_time < us_close_trigger and _MARKET_STATE.get('US') != 'OPEN':
                _MARKET_STATE['US'] = 'OPEN'
                send_telegram_message("🎯US | 🟢開盤")

    # 🌟 階段二：常規報價與警報擷取 (先處理最後一筆資料)
    # 大盤 15 分鐘常規廣播
    if is_monitoring:
        if process_tw:
            idx_interval_id = f"IDX_TW_{now_tpe.strftime('%Y%m%d_%H')}_{(now_tpe.minute // 15) * 15:02d}"
            if _ALERT_HISTORY.get('INDEX_TW') != idx_interval_id:
                idx_quotes = fetch_realtime_quotes(['^TWII'])
                if '^TWII' in idx_quotes:
                    q = idx_quotes['^TWII']
                    msg = build_qbs_tg_msg("TW", q['current'], q['change_pct'], is_manual=False)
                    send_telegram_message(msg)
                    _ALERT_HISTORY['INDEX_TW'] = idx_interval_id
                    
        if process_us:
            idx_interval_id = f"IDX_US_{now_us.strftime('%Y%m%d_%H')}_{(now_us.minute // 15) * 15:02d}"
            if _ALERT_HISTORY.get('INDEX_US') != idx_interval_id:
                idx_quotes = fetch_realtime_quotes(['^IXIC'])
                if '^IXIC' in idx_quotes:
                    q = idx_quotes['^IXIC']
                    msg = build_qbs_tg_msg("US", q['current'], q['change_pct'], is_manual=False)
                    send_telegram_message(msg)
                    _ALERT_HISTORY['INDEX_US'] = idx_interval_id

    # 為了維持 UI 全時段顯示，依然抓取所有目標的報價
    if targets_df.empty:
        return {}, []

    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    
    # 個股 5 分鐘警報
    if is_monitoring:
        for _, row in targets_df.iterrows():
            if row['ticker'] in quotes:
                is_tw_stock = '.TW' in row['ticker']
                if (process_tw and is_tw_stock) or (process_us and not is_tw_stock):
                    triggered = evaluate_alerts(row, quotes[row['ticker']], now_tpe)
                    all_triggered_alerts.extend(triggered)

    # 🌟 階段三：收盤判定與物理關門 (強制在最後一筆資料處理後執行)
    if is_monitoring:
        if now_tpe_time >= tw_close_trigger and _MARKET_STATE.get('TW') == 'OPEN':
            _MARKET_STATE['TW'] = 'CLOSED'
            send_telegram_message("🎯TW | 🔴收盤")
            
        if now_us_time >= us_close_trigger and _MARKET_STATE.get('US') == 'OPEN':
            _MARKET_STATE['US'] = 'CLOSED'
            send_telegram_message("🎯US | 🔴收盤")
            
    return quotes, all_triggered_alerts
