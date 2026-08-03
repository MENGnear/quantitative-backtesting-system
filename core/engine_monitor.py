# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.8.2 (Phase 7: 大盤滾動暴衝偵測版)
#
# 📋 進版說明 (Version Notes):
#   1. [暴衝偵測] 成功導入 MON_app 的 5 分鐘滾動視窗機制，精準捕捉大盤短線劇烈波動。
#   2. [防禦洗版] 針對暴衝警報加入獨立的 300 秒 (5分鐘) 冷卻鎖，確保警報高價值且不干擾。
#   3. [狀態精準化] 完整保留 v1.8.1 的開盤緩衝窗與 v1.8.0 的三層報價防護機制。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與狀態記憶體初始化 (🔥 新增滾動視窗記憶體)
#   - 2️⃣ 高頻報價與資料解析模組 (三層防護機制)
#   - 3️⃣ 警報觸發與冷卻邏輯
#   - 4️⃣ 引擎主程序 (🔥 階段二導入大盤暴衝偵測)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import pandas as pd
import yfinance as yf
import datetime
import pytz
import os
import logging
import numpy as np
from services.telegram_service import send_telegram_message, build_qbs_tg_msg
from core.repositories.monitor_repository import monitor_repo

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================================
# 1️⃣ 基礎環境與狀態記憶體初始化
# ==========================================================
_ALERT_HISTORY = {}
_MARKET_STATE = {'TW': 'CLOSED', 'US': 'CLOSED'}

# 🔥 大盤 5 分鐘滾動視窗專用記憶體
_INDEX_HISTORY = {'TW': [], 'US': []}
_INDEX_LAST_VOL_ALERT = {'TW': None, 'US': None}

def get_monitor_targets():
    """
    透過 monitor_repo 獲取監控標的 DataFrame。
    徹底與底層資料庫解耦。
    """
    return monitor_repo.get_monitor_targets_df()

# ==========================================================
# 2️⃣ 高頻報價與資料解析模組 (三層防護機制)
# ==========================================================
def get_realtime_price(ticker):
    """
    單檔股票三層降級報價防護：
    Tier 1: info API
    Tier 2: fast_info API
    Tier 3: history API (K線回推)
    """
    c_price, p_close, o_price = None, None, None
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Tier 1: 嘗試使用常規 info
        try:
            info = ticker_obj.info
            c_price = info.get('currentPrice', info.get('regularMarketPrice'))
            p_close = info.get('previousClose', info.get('regularMarketPreviousClose'))
            o_price = info.get('open', info.get('regularMarketOpen'))
        except Exception: 
            pass
            
        # Tier 2: 嘗試使用輕量化 fast_info
        if c_price is None or p_close is None:
            try:
                c_price = float(ticker_obj.fast_info['last_price'])
                p_close = float(ticker_obj.fast_info['previous_close'])
                o_price = float(ticker_obj.fast_info.get('open', c_price))
            except Exception: 
                pass
                
        # Tier 3: 最終底線 - 解析歷史 5 日 K 線
        if c_price is None or p_close is None:
            try:
                df = ticker_obj.history(period="5d", auto_adjust=False).dropna(subset=["Open", "Close"])
                if not df.empty and len(df) >= 2:
                    c_price = float(df['Close'].iloc[-1])
                    p_close = float(df['Close'].iloc[-2])
                    o_price = float(df['Open'].iloc[-1])
            except Exception: 
                pass
                
        return c_price, p_close, o_price
    except Exception as e:
        logging.error(f"[{ticker}] 報價引擎徹底失效: {e}")
        return None, None, None

def fetch_realtime_quotes(tickers):
    """逐檔抓取，取代原本容易被 Ban 的 yf.download 批量下載"""
    quotes = {}
    if not tickers:
        return quotes
        
    for ticker in tickers:
        c_price, p_close, o_price = get_realtime_price(ticker)
        
        if c_price is not None and p_close is not None:
            change_amt = c_price - p_close
            change_pct = (change_amt / p_close * 100) if p_close > 0 else 0.0
            
            quotes[ticker] = {
                'current': round(c_price, 2),
                'prev': round(p_close, 2),
                'open': round(o_price if o_price is not None else c_price, 2),
                'change_amt': round(change_amt, 2),
                'change_pct': round(change_pct, 2)
            }
        else:
            logging.warning(f"⚠️ [{ticker}] 三層防護皆無法獲取報價，略過本次更新。")
            
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
    global _MARKET_STATE, _INDEX_HISTORY, _INDEX_LAST_VOL_ALERT
    targets_df = get_monitor_targets()
    
    # 建立精確的時區時間 (US/Eastern 自動處理夏/冬令切換)
    now_tpe = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
    now_us = now_tpe.astimezone(pytz.timezone('US/Eastern'))
    
    now_tpe_time = now_tpe.time()
    now_us_time = now_us.time()
    
    # 定義精確的開關盤節點與智慧緩衝時間窗 (5分鐘)
    tw_open = datetime.time(9, 0)
    tw_open_buffer = datetime.time(9, 5)
    tw_close_trigger = datetime.time(13, 30)
    tw_close_process = datetime.time(13, 30, 59)
    
    us_open = datetime.time(9, 30)
    us_open_buffer = datetime.time(9, 35)
    us_close_trigger = datetime.time(16, 0)
    us_close_process = datetime.time(16, 0, 59)
    
    process_tw = False
    process_us = False

    # 🌟 階段一：開盤判定與狀態更新 (加入盤中判定)
    if is_monitoring:
        if tw_open <= now_tpe_time <= tw_close_process:
            process_tw = True
            if now_tpe_time < tw_close_trigger and _MARKET_STATE.get('TW') != 'OPEN':
                _MARKET_STATE['TW'] = 'OPEN'
                if now_tpe_time <= tw_open_buffer:
                    send_telegram_message("🎯TW | 🟢開盤")
                else:
                    send_telegram_message("🎯TW | 🟢盤中")
                
        if us_open <= now_us_time <= us_close_process:
            process_us = True
            if now_us_time < us_close_trigger and _MARKET_STATE.get('US') != 'OPEN':
                _MARKET_STATE['US'] = 'OPEN'
                if now_us_time <= us_open_buffer:
                    send_telegram_message("🎯US | 🟢開盤")
                else:
                    send_telegram_message("🎯US | 🟢盤中")

    # 🌟 階段二：常規報價與警報擷取 (加入大盤滾動暴衝偵測)
    if is_monitoring:
        if process_tw:
            idx_quotes = fetch_realtime_quotes(['^TWII'])
            if '^TWII' in idx_quotes:
                q = idx_quotes['^TWII']
                curr_price = q['current']
                
                # 1) 15 分鐘常規大盤廣播
                idx_interval_id = f"IDX_TW_{now_tpe.strftime('%Y%m%d_%H')}_{(now_tpe.minute // 15) * 15:02d}"
                if _ALERT_HISTORY.get('INDEX_TW') != idx_interval_id:
                    msg = build_qbs_tg_msg("TW", curr_price, q['change_pct'], is_manual=False)
                    send_telegram_message(msg)
                    _ALERT_HISTORY['INDEX_TW'] = idx_interval_id
                
                # 2) 5 分鐘滾動視窗暴衝偵測
                history = _INDEX_HISTORY['TW']
                history.append((now_tpe, curr_price))
                cutoff = now_tpe - datetime.timedelta(minutes=5)
                history = [(t, p) for t, p in history if t >= cutoff]
                _INDEX_HISTORY['TW'] = history
                
                if len(history) > 1:
                    oldest_t, oldest_p = history[0]
                    time_diff_sec = (now_tpe - oldest_t).total_seconds()
                    
                    if time_diff_sec >= 240: 
                        vol_pct = (curr_price - oldest_p) / oldest_p * 100
                        vol_diff = curr_price - oldest_p
                        
                        if abs(vol_pct) >= 5.0: 
                            last_alert = _INDEX_LAST_VOL_ALERT.get('TW')
                            if last_alert is None or (now_tpe - last_alert).total_seconds() >= 300:
                                vol_sign = "+" if vol_pct > 0 else ""
                                vol_arrow = "↑" if vol_pct > 0 else "↓"
                                time_str = now_tpe.strftime('%H:%M')
                                msg = f"🕒{time_str} | 🎯TW MktIdx | 🔥暴衝 | {'📈' if vol_pct > 0 else '📉'}{vol_sign}{vol_diff:,.2f} ({vol_arrow}{abs(vol_pct):.2f}%)"
                                send_telegram_message(msg)
                                _INDEX_LAST_VOL_ALERT['TW'] = now_tpe
                                
        if process_us:
            idx_quotes = fetch_realtime_quotes(['^IXIC'])
            if '^IXIC' in idx_quotes:
                q = idx_quotes['^IXIC']
                curr_price = q['current']
                
                # 1) 15 分鐘常規大盤廣播
                idx_interval_id = f"IDX_US_{now_us.strftime('%Y%m%d_%H')}_{(now_us.minute // 15) * 15:02d}"
                if _ALERT_HISTORY.get('INDEX_US') != idx_interval_id:
                    msg = build_qbs_tg_msg("US", curr_price, q['change_pct'], is_manual=False)
                    send_telegram_message(msg)
                    _ALERT_HISTORY['INDEX_US'] = idx_interval_id
                    
                # 2) 5 分鐘滾動視窗暴衝偵測
                history = _INDEX_HISTORY['US']
                history.append((now_us, curr_price))
                cutoff = now_us - datetime.timedelta(minutes=5)
                history = [(t, p) for t, p in history if t >= cutoff]
                _INDEX_HISTORY['US'] = history
                
                if len(history) > 1:
                    oldest_t, oldest_p = history[0]
                    time_diff_sec = (now_us - oldest_t).total_seconds()
                    
                    if time_diff_sec >= 240: 
                        vol_pct = (curr_price - oldest_p) / oldest_p * 100
                        vol_diff = curr_price - oldest_p
                        
                        if abs(vol_pct) >= 5.0: 
                            last_alert = _INDEX_LAST_VOL_ALERT.get('US')
                            if last_alert is None or (now_us - last_alert).total_seconds() >= 300:
                                vol_sign = "+" if vol_pct > 0 else ""
                                vol_arrow = "↑" if vol_pct > 0 else "↓"
                                time_str = now_us.strftime('%H:%M')
                                msg = f"🕒{time_str} | 🎯US MktIdx | 🔥暴衝 | {'📈' if vol_pct > 0 else '📉'}{vol_sign}{vol_diff:,.2f} ({vol_arrow}{abs(vol_pct):.2f}%)"
                                send_telegram_message(msg)
                                _INDEX_LAST_VOL_ALERT['US'] = now_us

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

    # 🌟 階段三：收盤判定與物理關門
    if is_monitoring:
        if now_tpe_time >= tw_close_trigger and _MARKET_STATE.get('TW') == 'OPEN':
            _MARKET_STATE['TW'] = 'CLOSED'
            send_telegram_message("🎯TW | 🔴收盤")
            
        if now_us_time >= us_close_trigger and _MARKET_STATE.get('US') == 'OPEN':
            _MARKET_STATE['US'] = 'CLOSED'
            send_telegram_message("🎯US | 🔴收盤")
            
    return quotes, all_triggered_alerts
