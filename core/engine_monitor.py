# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.3.0 (Phase 6.5: Telegram 自動推播與五分鐘防洗頻機制)
#
# 📋 進版說明 (Version Notes):
#   1. [核心重構] 徹底分離台股與美股的 yf.download 請求，防止時差與休市導致的 NaN 空值互相干擾，修復美股無法讀取問題。
#   2. [推播升級] (v1.3.0) 串接 telegram_service，實作自動推播單行極簡格式。
#   3. [防洗機制] (v1.3.0) 導入 5 分鐘 (個股) 與 15 分鐘 (大盤) 的區間鎖定 Bucket 演算法，徹底根除洗頻問題。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與冷卻記憶體初始化 (🔥 升級 Bucket 記憶體)
#   - 2️⃣ 高頻報價與資料解析模組 (分流機制)
#   - 3️⃣ 警報觸發與冷卻邏輯 (🔥 導入 MON 觸發條件與 5 分鐘防護)
#   - 4️⃣ 引擎主程序 (🔥 導入 15 分鐘大盤輪播)
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
# 儲存 Bucket ID，例如 {'2330.TW': '20260726_10_05', 'INDEX': '20260726_10_15'}
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
# 3️⃣ 警報觸發與冷卻邏輯 (🔥 導入 MON 邏輯與 5 分鐘 Bucket)
# ==========================================================
def evaluate_alerts(row, quote, tz_now):
    ticker = row['ticker']
    current_price = quote['current']
    change_pct = quote['change_pct']
    
    # 萃取乾淨名稱用於推播
    clean_name = str(row['display_name']).strip()
    if not clean_name or clean_name == ticker:
        clean_name = ticker.replace('.TW', '')
    
    alerts = []
    thresholds = parse_custom_values(row['thresholds'])
    entry_prices = parse_custom_values(row['entry_prices'])
    exit_prices = parse_custom_values(row['exit_prices'])

    is_triggered = False
    trigger_reasons = []

    # 1. 檢查門檻 (漲跌幅絕對值)
    for th in thresholds:
        if abs(change_pct) >= th:
            is_triggered = True
            trigger_reasons.append(f"達標 {th}%")
            break

    # 2. 檢查進場 (現價 >= 設定值)
    for entry in entry_prices:
        if current_price >= entry:
            is_triggered = True
            trigger_reasons.append(f"進場達標")
            break

    # 3. 檢查出場 (現價 <= 設定值)
    for exit_p in exit_prices:
        if current_price <= exit_p:
            is_triggered = True
            trigger_reasons.append(f"出場達標")
            break

    if is_triggered:
        # 紀錄 UI 顯示用的警報
        reason_str = "及".join(trigger_reasons)
        alerts.append({'ticker': ticker, 'type': '🚨 觸發', 'message': f"{reason_str} (${current_price})"})
        
        # 5 分鐘區間防洗頻鎖定 (Bucket Lock)
        # 格式範例: 20260726_10_05
        current_interval_id = f"{tz_now.strftime('%Y%m%d_%H')}_{(tz_now.minute // 5) * 5:02d}"
        
        if _ALERT_HISTORY.get(ticker) != current_interval_id:
            # 發送單行極簡 Telegram
            msg = build_qbs_tg_msg(clean_name, current_price, change_pct, is_manual=False)
            send_telegram_message(msg)
            # 鎖定該 5 分鐘區間
            _ALERT_HISTORY[ticker] = current_interval_id

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序 (🔥 導入大盤 15 分鐘輪播)
# ==========================================================
def run_radar_scan():
    targets_df = get_monitor_targets()
    tz_now = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    
    # --- A. 大盤 15 分鐘固定推播機制 ---
    is_tw_time = 6 <= tz_now.hour <= 18
    target_idx = '^TWII' if is_tw_time else '^IXIC'
    idx_name = "TW" if is_tw_time else "US"
    
    # 15 分鐘區間防洗頻鎖定 (Bucket Lock)
    # 格式範例: IDX_20260726_10_15
    idx_interval_id = f"IDX_{tz_now.strftime('%Y%m%d_%H')}_{(tz_now.minute // 15) * 15:02d}"
    
    if _ALERT_HISTORY.get('INDEX') != idx_interval_id:
        idx_quotes = fetch_realtime_quotes([target_idx])
        if target_idx in idx_quotes:
            q = idx_quotes[target_idx]
            msg = build_qbs_tg_msg(idx_name, q['current'], q['change_pct'], is_manual=False)
            send_telegram_message(msg)
            _ALERT_HISTORY['INDEX'] = idx_interval_id
            
    # --- B. 個股雷達掃描與自動警報 ---
    if targets_df.empty:
        return {}, []

    tickers = targets_df['ticker'].tolist()
    quotes = fetch_realtime_quotes(tickers)
    
    all_triggered_alerts = []
    for _, row in targets_df.iterrows():
        if row['ticker'] in quotes:
            triggered = evaluate_alerts(row, quotes[row['ticker']], tz_now)
            all_triggered_alerts.extend(triggered)
            
    return quotes, all_triggered_alerts
