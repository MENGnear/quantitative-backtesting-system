# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_monitor.py
# 程式版本 : monitor_v1.10.0 (Phase 8: 幽靈報價與死水防護終極版)
#
# 📋 進版說明 (Version Notes):
#   1. [全域時間戳] 拔除嚴重快取延遲的 .info 屬性，全面依賴 history 進行嚴格的 Date() 驗證，杜絕時空穿越報價。
#   2. [價格指紋鎖] 升級 _ALERT_HISTORY，新增 last_price 比對。冷卻解鎖後若價格未跳動(死水)，強制靜音防洗版。
#   3. [大盤正名] 將大盤廣播代碼修正為 TW MktIdx / US MktIdx，避免與股票代碼混淆。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與狀態記憶體初始化 (🔥 升級為指紋記憶體)
#   - 2️⃣ 高頻報價與資料解析模組 (🔥 拔除 info，嚴格時間戳)
#   - 3️⃣ 警報觸發與冷卻邏輯 (🔥 導入價格指紋鎖)
#   - 4️⃣ 引擎主程序
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
# 🔥 升級為字典結構儲存: {'interval_id': str, 'price': float}
_ALERT_HISTORY = {}
_MARKET_STATE = {'TW': 'CLOSED', 'US': 'CLOSED'}

# 大盤 5 分鐘滾動視窗專用記憶體
_INDEX_HISTORY = {'TW': [], 'US': []}
_INDEX_LAST_VOL_ALERT = {'TW': None, 'US': None}

def get_monitor_targets():
    """
    透過 monitor_repo 獲取監控標的 DataFrame。
    徹底與底層資料庫解耦。
    """
    return monitor_repo.get_monitor_targets_df()

# ==========================================================
# 2️⃣ 高頻報價與資料解析模組 (🔥 拔除 info，嚴格時間戳)
# ==========================================================
def get_realtime_price(ticker, market_now):
    """
    單檔股票雙層報價防護 (強制日期驗證)：
    Tier 1: history API (最可靠的時間戳來源)
    Tier 2: fast_info API (輕量備援)
    """
    c_price, p_close, o_price = None, None, None
    vol = 0
    is_today = False
    
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Tier 1: 首選 history 5d，以取得絕對可靠的日期驗證
        try:
            df = ticker_obj.history(period="5d", auto_adjust=False).dropna(subset=["Open", "Close"])
            if not df.empty and len(df) >= 2:
                c_price = float(df['Close'].iloc[-1])
                p_close = float(df['Close'].iloc[-2])
                o_price = float(df['Open'].iloc[-1])
                vol = float(df['Volume'].iloc[-1])
                
                # 嚴格驗證資料日期是否為當地今日
                last_date = df.index[-1].date()
                if last_date == market_now.date():
                    is_today = True 
        except Exception: 
            pass
            
        # Tier 2: 若 history 失敗，嘗試使用輕量化 fast_info 作為底線
        if c_price is None or p_close is None:
            try:
                c_price = float(ticker_obj.fast_info['last_price'])
                p_close = float(ticker_obj.fast_info['previous_close'])
                o_price = float(ticker_obj.fast_info.get('open', c_price))
                vol = float(ticker_obj.fast_info.get('last_volume', 0))
                # fast_info 無法確保日期，為防開盤幽靈，預設 is_today = False 讓外層去濾
            except Exception: 
                pass
                
        return c_price, p_close, o_price, vol, is_today
    except Exception as e:
        logging.error(f"[{ticker}] 報價引擎徹底失效: {e}")
        return None, None, None, 0, False

def fetch_realtime_quotes(tickers):
    """逐檔抓取，並導入幽靈報價與試撮虛價雙重濾網"""
    quotes = {}
    if not tickers:
        return quotes
        
    for ticker in tickers:
        is_tw = '.TW' in ticker or ticker == '^TWII'
        market_tz = pytz.timezone('Asia/Taipei') if is_tw else pytz.timezone('US/Eastern')
        market_now = datetime.datetime.now(market_tz)
        
        c_price, p_close, o_price, vol, is_today = get_realtime_price(ticker, market_now)
        
        if c_price is not None and p_close is not None:
            # 🛡️ 濾網 1：昨天舊資料攔截 (解決時空穿越與 09:00 卡頓轟炸)
            if not is_today and market_now.time() >= datetime.time(9, 0):
                logging.info(f"⏳ [{ticker}] 尚無今日即時報價，攔截幽靈舊資料。")
                continue
                
            # 🛡️ 濾網 2：試撮與零成交濾網 (09:00 ~ 09:02)
            if datetime.time(9, 0) <= market_now.time() <= datetime.time(9, 2):
                if vol <= 0:
                    logging.info(f"⏳ [{ticker}] 開盤試撮階段無成交量，攔截虛價。")
                    continue
                    
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
            logging.warning(f"⚠️ [{ticker}] 防護皆無法獲取報價，略過本次更新。")
            
    return quotes

def parse_custom_values(val_str):
    if not val_str or pd.isna(val_str):
        return []
    try:
        return [float(x.strip()) for x in str(val_str).split(',') if x.strip()]
    except Exception:
        return []

# ==========================================================
# 3️⃣ 警報觸發與冷卻邏輯 (🔥 導入價格指紋鎖)
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
        
        # 讀取歷史指紋紀錄
        last_record = _ALERT_HISTORY.get(ticker, {})
        last_interval = last_record.get('interval_id')
        last_price = last_record.get('price')
        
        if last_interval != current_interval_id:
            # 🛡️ 價格指紋鎖：冷卻解鎖，但價格一毛未跳 (死水)，強制阻擋！
            if last_price is not None and abs(current_price - last_price) < 0.0001:
                logging.info(f"🛑 [{ticker}] 觸發死水防護鎖，攔截定時重複推播。")
                _ALERT_HISTORY[ticker] = {'interval_id': current_interval_id, 'price': current_price}
            else:
                msg = build_qbs_tg_msg(clean_name, current_price, change_pct, is_manual=False)
                send_telegram_message(msg)
                _ALERT_HISTORY[ticker] = {'interval_id': current_interval_id, 'price': current_price}

    return alerts

# ==========================================================
# 4️⃣ 引擎主程序
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

    # 🌟 階段一：開盤判定與狀態更新
    if is_monitoring:
        if tw_open <= now_tpe_time <= tw_close_process:
            process_tw = True
            if now_tpe_time < tw_close_trigger and _MARKET_STATE.get('TW') != 'OPEN':
                _MARKET_STATE['TW'] = 'OPEN'
                if now_tpe_time <= tw_open_buffer:
                    send_telegram_message("🎯TW MktIdx | 🟢開盤")
                else:
                    send_telegram_message("🎯TW MktIdx | 🟢盤中")
                
        if us_open <= now_us_time <= us_close_process:
            process_us = True
            if now_us_time < us_close_trigger and _MARKET_STATE.get('US') != 'OPEN':
                _MARKET_STATE['US'] = 'OPEN'
                if now_us_time <= us_open_buffer:
                    send_telegram_message("🎯US MktIdx | 🟢開盤")
                else:
                    send_telegram_message("🎯US MktIdx | 🟢盤中")

    # 🌟 階段二：常規報價與警報擷取 (加入大盤滾動暴衝與指紋鎖)
    if is_monitoring:
        if process_tw:
            idx_quotes = fetch_realtime_quotes(['^TWII'])
            if '^TWII' in idx_quotes:
                q = idx_quotes['^TWII']
                curr_price = q['current']
                
                # 1) 15 分鐘常規大盤廣播 (導入價格指紋鎖)
                idx_interval_id = f"IDX_TW_{now_tpe.strftime('%Y%m%d_%H')}_{(now_tpe.minute // 15) * 15:02d}"
                last_idx_record = _ALERT_HISTORY.get('INDEX_TW', {})
                
                if last_idx_record.get('interval_id') != idx_interval_id:
                    last_idx_price = last_idx_record.get('price')
                    if last_idx_price is not None and abs(curr_price - last_idx_price) < 0.0001:
                        # 死水防護
                        _ALERT_HISTORY['INDEX_TW'] = {'interval_id': idx_interval_id, 'price': curr_price}
                    else:
                        msg = build_qbs_tg_msg("TW MktIdx", curr_price, q['change_pct'], is_manual=False)
                        send_telegram_message(msg)
                        _ALERT_HISTORY['INDEX_TW'] = {'interval_id': idx_interval_id, 'price': curr_price}
                
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
                
                # 1) 15 分鐘常規大盤廣播 (導入價格指紋鎖)
                idx_interval_id = f"IDX_US_{now_us.strftime('%Y%m%d_%H')}_{(now_us.minute // 15) * 15:02d}"
                last_idx_record = _ALERT_HISTORY.get('INDEX_US', {})
                
                if last_idx_record.get('interval_id') != idx_interval_id:
                    last_idx_price = last_idx_record.get('price')
                    if last_idx_price is not None and abs(curr_price - last_idx_price) < 0.0001:
                        # 死水防護
                        _ALERT_HISTORY['INDEX_US'] = {'interval_id': idx_interval_id, 'price': curr_price}
                    else:
                        msg = build_qbs_tg_msg("US MktIdx", curr_price, q['change_pct'], is_manual=False)
                        send_telegram_message(msg)
                        _ALERT_HISTORY['INDEX_US'] = {'interval_id': idx_interval_id, 'price': curr_price}
                    
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
            send_telegram_message("🎯TW MktIdx | 🔴收盤")
            
        if now_us_time >= us_close_trigger and _MARKET_STATE.get('US') == 'OPEN':
            _MARKET_STATE['US'] = 'CLOSED'
            send_telegram_message("🎯US MktIdx | 🔴收盤")
            
    return quotes, all_triggered_alerts
