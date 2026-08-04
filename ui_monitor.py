# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_monitor_v2.0.0 (Phase 7: 防呆與雙層刪除版)
#
# 📋 進版說明 (Version Notes):
#   1. [防呆驗證] 新增「嚴格入庫防呆機制」，輸入股號時強制進行 1d K線驗證，擋下無效/下市股票。
#   2. [雙層刪除] 重構移除區塊為「停止監測」與「徹底刪除字典股號」雙軌制，保持雲端資料庫潔癖。
#   3. [狀態聯動] 暫停按鈕正式聯動後端引擎 (engine_monitor)，清空快取避免盤中重啟時發生延遲。
#   4. [UI 解耦] 刷新頻率 Slider 的 Key 與記憶體變數解耦，解決跨頁面失憶問題。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 工具函式 (名稱解析與字串處理)
#   - 2️⃣ 側邊欄渲染 (包含防呆新增、雙層刪除、頻率設定)
#   - 3️⃣ 監控主畫面渲染 (戰情卡片矩陣)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import pytz
import re
import requests
from core import engine_monitor
from core.repositories.monitor_repository import monitor_repo
from services.telegram_service import send_telegram_message

# ==========================================================
# 1️⃣ 工具函式 (名稱解析與字串處理)
# ==========================================================
def get_smart_display_name(sym, stock_dict, save_stock_dict):
    """智慧獲取台股中文名稱，若無則爬取 Yahoo 網頁並快取"""
    if sym in stock_dict:
        return stock_dict[sym].replace(".TW", "")
    
    display_name = sym
    if ".TW" in sym.upper():
        code = sym.upper().replace(".TW", "")
        try:
            res = requests.get(f"https://tw.stock.yahoo.com/quote/{code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            match = re.search(r'<title>(.*?)\(', res.text)
            if match:
                chinese_name = match.group(1).strip()
                display_name = f"{code} {chinese_name}"
            else:
                display_name = code
        except:
            display_name = code
            
    stock_dict[sym] = display_name
    save_stock_dict(stock_dict)
    return display_name.replace(".TW", "")

# ==========================================================
# 2️⃣ 側邊欄渲染 (Micro-Frontend Hook)
# ==========================================================
def render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header):
    sidebar_header("⚙️", "雷達監測控制面板")

    # --------------------------------------------------------
    # ▶️ 執行股票監測 (🔥 包含狀態重置聯動)
    # --------------------------------------------------------
    with st.container(border=True):
        st.markdown("### ▶️ 執行股票監測")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("開始", use_container_width=True): 
                if not st.session_state.monitoring:
                    st.session_state.monitoring = True
                    # (推播通知交由 engine_monitor 的 run_radar_scan 統一判斷)
        with col_btn2:
            if st.button("暫停", use_container_width=True): 
                if st.session_state.monitoring:
                    st.session_state.monitoring = False
                    
                    # 判斷時區發送暫停通知
                    now_utc = datetime.datetime.now(datetime.timezone.utc)
                    tpe_now = now_utc.astimezone(pytz.timezone('Asia/Taipei'))
                    us_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
                    if datetime.time(6, 1) <= tpe_now.time() <= datetime.time(18, 0):
                        send_telegram_message(f"🕒{tpe_now.strftime('%H:%M')} | 🎯TW MktIdx | 🟡暫停監測")
                    else:
                        send_telegram_message(f"🕒{us_now.strftime('%H:%M')} | 🎯US MktIdx | 🟡暫停監測")
                    
                    # 🔥 聯動清空引擎狀態 (解決盤中重啟被略過的問題)
                    engine_monitor._MARKET_STATE = {'TW': 'CLOSED', 'US': 'CLOSED'}
                    engine_monitor._ALERT_HISTORY.clear()
                    
        if st.session_state.monitoring: st.success("🟢 系統即時監測中...")
        else: st.info("🟡 監測暫停中")

    # --------------------------------------------------------
    # ➕ 新增監測股票 (🔥 包含嚴格防呆入庫)
    # --------------------------------------------------------
    with st.container(border=True):
        st.markdown("### ➕ 新增監測股票")
        
        # 📂 字典庫選取
        st.markdown("<div style='color:#38bdf8; font-size:1.0rem; font-weight:700; margin-top:5px; margin-bottom:5px;'>📂 從雲端字典選取</div>", unsafe_allow_html=True)
        market_choice = st.radio("選擇市場", ["🇹🇼 台灣", "🇺🇸 美國"], horizontal=True, label_visibility="collapsed", key="add_market")
        
        if "台灣" in market_choice:
            selected_db = st.selectbox("🇹🇼 字典選取", tw_options, format_func=format_tw_option, key="db_tw")
        else:
            selected_db = st.selectbox("🇺🇸 字典選取", us_options, format_func=lambda x: stock_dict.get(x, x), key="db_us")
            
        th_db = st.text_input("提醒門檻 (%)", placeholder="例: 5, 10", key="th_db")
        en_db = st.text_input("進場提醒 ($)", placeholder="例: 150 (>= 觸發)", key="en_db")
        ex_db = st.text_input("出場提醒 ($)", placeholder="例: 140 (<= 觸發)", key="ex_db")
        
        def process_and_validate(target_sym, th_text, en_text, ex_text):
            if target_sym and target_sym != "--- 請選擇 ---":
                with st.spinner(f"🔍 驗證 {target_sym} 中..."):
                    # 🔥 嚴格防呆：即時驗證股票有效性
                    try:
                        test_df = yf.Ticker(target_sym).history(period="1d")
                        if test_df.empty:
                            st.error(f"❌ 查無股票代碼 {target_sym} 或已下市，拒絕寫入！")
                            return
                    except Exception:
                        st.error(f"❌ 查詢 {target_sym} 發生連線錯誤，請稍後再試！")
                        return
                    
                    # 確保寫入字典
                    get_smart_display_name(target_sym, stock_dict, save_stock_dict)
                    
                    # 寫入資料庫 Repo (若您的 repo 方法名稱不同，請於此處微調)
                    try:
                        monitor_repo.add_target(target_sym, th_text, en_text, ex_text)
                        st.success(f"✅ {target_sym} 驗證成功並已加入雷達！")
                        st.rerun()
                    except Exception as e:
                        st.warning(f"寫入資料庫失敗: {e}")

        if st.button("確認加入監測", use_container_width=True, key="btn_add_db"):
            process_and_validate(selected_db, th_db, en_db, ex_db)
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        
        # ✍️ 手動輸入
        st.markdown("<div style='color:#38bdf8; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>✍️ 手動輸入新股票</div>", unsafe_allow_html=True)
        new_sym = st.text_input("輸入代碼", placeholder="例: AAPL 或 2330", key="sym_manual").strip().upper()
        th_man = st.text_input("提醒門檻 (%)", placeholder="例: 5, 10", key="th_man")
        en_man = st.text_input("進場提醒 ($)", placeholder="例: 150", key="en_man")
        ex_man = st.text_input("出場提醒 ($)", placeholder="例: 140", key="ex_man")
        
        if st.button("驗證並寫入系統", use_container_width=True, key="btn_add_man"): 
            if new_sym and new_sym[0].isdigit() and ".TW" not in new_sym: 
                new_sym += ".TW"
            process_and_validate(new_sym, th_man, en_man, ex_man)

    # --------------------------------------------------------
    # 🗑️ 移除與管理標的 (🔥 雙層刪除系統)
    # --------------------------------------------------------
    with st.container(border=True):
        st.markdown("### 🗑️ 移除與管理標的")
        del_mode = st.radio("選擇操作", ["🛑 停止雷達監測", "🗑️ 徹底刪除字典股號"], horizontal=True, label_visibility="collapsed")
        
        if "停止雷達監測" in del_mode:
            st.markdown("<div style='color:#94a3b8; font-size:0.82rem; margin-bottom:8px;'>從目前的監控池移除，但保留在雲端字典中。</div>", unsafe_allow_html=True)
            active_df = engine_monitor.get_monitor_targets()
            active_tickers = active_df['ticker'].tolist() if not active_df.empty else []
            display_opts = {sym: stock_dict.get(sym, sym).replace(".TW", "") for sym in active_tickers}
            del_sym = st.selectbox("選擇停止監測的標的", ["--- 請選擇 ---"] + active_tickers, format_func=lambda x: display_opts.get(x, x) if x != "--- 請選擇 ---" else x)
            
            if st.button("確認停止", use_container_width=True) and del_sym != "--- 請選擇 ---":
                try: 
                    monitor_repo.delete_target(del_sym) # 呼叫 Repo 移除
                    st.success(f"✅ 已停止監測 {del_sym}")
                    st.rerun()
                except Exception as e: st.warning(f"操作失敗: {e}")
                
        else:
            st.markdown("<div style='color:#ef4444; font-size:0.82rem; margin-bottom:8px;'>⚠️ 從雲端字典中徹底抹除，不再出現於下拉選單。</div>", unsafe_allow_html=True)
            all_dict_keys = sorted(list(stock_dict.keys()))
            display_opts = {sym: stock_dict.get(sym, sym).replace(".TW", "") for sym in all_dict_keys}
            purge_sym = st.selectbox("選擇徹底刪除的股號", ["--- 請選擇 ---"] + all_dict_keys, format_func=lambda x: display_opts.get(x, x) if x != "--- 請選擇 ---" else x)
            
            if st.button("確認徹底刪除", use_container_width=True) and purge_sym != "--- 請選擇 ---":
                # 1. 從字典抹除
                stock_dict.pop(purge_sym, None)
                save_stock_dict(stock_dict)
                # 2. 保險起見，同步從監控池抹除
                try: monitor_repo.delete_target(purge_sym)
                except: pass
                st.success(f"🗑️ 已徹底刪除 {purge_sym}")
                st.rerun()

    # --------------------------------------------------------
    # ⏱️ 網頁刷新頻率 (🔥 UI 解耦，防失憶)
    # --------------------------------------------------------
    with st.container(border=True):
        st.markdown("### ⏱️ 網頁刷新頻率")
        # 確保記憶體中有永久存在的預設值
        if "refresh_a_val" not in st.session_state:
            st.session_state.refresh_a_val = 30
            
        # 將 Key 改為專屬的 UI Key (refresh_sec_ui_a)
        refresh_sec_a = st.slider("秒", 5, 60, st.session_state.refresh_a_val, key="refresh_sec_ui_a", label_visibility="collapsed")
        
        # 寫回永久記憶體
        st.session_state.refresh_a_val = refresh_sec_a
        st.session_state.refresh_a = refresh_sec_a
        
        if st.button("🔄 手動立即刷新", use_container_width=True):
            st.rerun()

# ==========================================================
# 3️⃣ 監控主畫面渲染 (Micro-Frontend Hook)
# ==========================================================
def render_telegram_manual_test_ui():
    """保留給手動測試推播元件的擴充槽"""
    with st.sidebar:
        with st.container(border=True):
            st.markdown("### 🛠️ 手動測試推播")
            if st.button("發送目前小卡狀態", use_container_width=True):
                st.session_state.trigger_manual_push = True

def render_radar_dashboard():
    """主畫面戰情室卡片渲染"""
    
    # 透過 engine_monitor 獲取最新報價與警報
    quotes, triggered_alerts = engine_monitor.run_radar_scan(st.session_state.monitoring)
    targets_df = engine_monitor.get_monitor_targets()
    
    if targets_df.empty:
        st.info("📭 目前清單中沒有股票，請由側邊欄新增。")
        return
        
    # 簡單的卡片矩陣展示 (延續 MON_app 的深色風格)
    matrix_html = '<div class="flex-matrix-container" style="display: flex; flex-wrap: wrap; gap: 14px;">'
    
    for _, row in targets_df.iterrows():
        sym = row['ticker']
        if sym not in quotes:
            continue
            
        q = quotes[sym]
        c_price = q['current']
        p_close = q['prev']
        change_pct = q['change_pct']
        change_amt = q['change_amt']
        
        is_up = change_amt >= 0
        is_tw = ".TW" in sym
        
        # 沿用 MON 的紅綠反轉美學
        card_bg = ("rgba(239, 68, 68, 0.12)" if is_up else "rgba(16, 185, 129, 0.12)") if is_tw else ("rgba(16, 185, 129, 0.12)" if is_up else "rgba(239, 68, 68, 0.12)")
        card_border = ("rgba(239, 68, 68, 0.35)" if is_up else "rgba(16, 185, 129, 0.35)") if is_tw else ("rgba(16, 185, 129, 0.35)" if is_up else "rgba(239, 68, 68, 0.35)")
        badge_color = ("#ef4444" if is_up else "#10b981") if is_tw else ("#10b981" if is_up else "#ef4444")
        
        display_name = sym.replace(".TW", "")
        
        matrix_html += f"""
        <div style="background-color: #171a23; border: 1px solid {card_border}; border-radius: 12px; padding: 16px; width: 295px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
            <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff; margin-bottom: 2px;">{display_name}</div>
            <div style="color: #38bdf8; font-size: 1.9rem; font-weight: 700; margin-bottom: 10px;">${c_price:.2f}</div>
            <div style="display: flex; justify-content: space-between;">
                <div style="flex: 1; border-right: 1px dashed #2d3748; padding-right: 8px;">
                    <span style="color: #94a3b8; font-size: 0.85rem;">昨收：</span><span style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600;">${p_close:.2f}</span><br>
                    <span style="color: #94a3b8; font-size: 0.85rem;">漲幅：</span><span style="color: {badge_color}; font-size: 0.85rem; font-weight: 600;">{change_amt:+.2f} ({change_pct:+.2f}%)</span>
                </div>
                <div style="flex: 1; padding-left: 8px;">
                    <span style="color: #a78bfa; font-size: 0.85rem;">門檻：</span><span style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600;">{row['thresholds']}</span><br>
                    <span style="color: #a78bfa; font-size: 0.85rem;">進場：</span><span style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600;">{row['entry_prices']}</span><br>
                    <span style="color: #a78bfa; font-size: 0.85rem;">出場：</span><span style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600;">{row['exit_prices']}</span>
                </div>
            </div>
        </div>
        """
    
    matrix_html += '</div>'
    st.markdown(matrix_html, unsafe_allow_html=True)
