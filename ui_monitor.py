# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.10.1 (Pre-Phase 7: 微前端側邊欄解耦 + 完整戰情室排版復原)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 完整保留 render_sidebar 側邊欄業務邏輯，維持微前端解耦。
#   2. [重大修復] 完全復原您原本精雕細琢的 render_radar_dashboard HTML/CSS 戰情室排版。
#   3. [功能對齊] 整合 TW 與 US 市場分組渲染、智慧去重與動態漲跌幅卡片。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 側邊欄渲染 (Micro-Frontend)
#   - 2️⃣ 手動推播測試元件
#   - 3️⃣ 主畫面戰情室 (含 TW/US 分組與精美 HTML 小卡排版)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import textwrap
from core import db_manager
from core import engine_monitor
from services.telegram_service import send_telegram_message

# ==========================================================
# 1️⃣ 側邊欄渲染 (Micro-Frontend)
# ==========================================================
def render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header):
    if "sel_tw_val" not in st.session_state: st.session_state.sel_tw_val = "--- 請選擇 ---"
    if "sel_us_val" not in st.session_state: st.session_state.sel_us_val = "--- 請選擇 ---"
    if "manual_sym_val" not in st.session_state: st.session_state.manual_sym_val = ""
    if "clear_input_flag" not in st.session_state: st.session_state.clear_input_flag = False

    def on_sel_change(): st.session_state.manual_sym_val = ""
    def on_manual_change():
        if st.session_state.manual_sym_val.strip() != "":
            st.session_state.sel_tw_val = "--- 請選擇 ---"
            st.session_state.sel_us_val = "--- 請選擇 ---"

    monitor_items = db_manager.get_all_monitor_items()
    monitor_tickers = [item['ticker'] for item in monitor_items]
    
    monitor_map = {}
    for item in monitor_items:
        t = item['ticker']
        ct = t.replace('.TW', '')
        dn = str(item['display_name']).strip()
        if not dn or dn == t or dn == ct: monitor_map[t] = f"{ct}"
        elif dn.startswith(ct): monitor_map[t] = f"{dn}"
        else: monitor_map[t] = f"{ct} {dn}"

    with st.container(border=True):
        sidebar_header("▶️", "執行股票監測")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("開始", use_container_width=True, key="start_mon"): 
                if not st.session_state.monitoring:
                    st.session_state.monitoring = True
                    now_tpe = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
                    prefix = "TW" if 6 <= now_tpe.hour <= 18 else "US"
                    send_telegram_message(f"🎯{prefix} | 🟢開始監測")
        with col_btn2:
            if st.button("暫停", use_container_width=True, key="stop_mon"): 
                if st.session_state.monitoring:
                    st.session_state.monitoring = False
                    now_tpe = datetime.datetime.now(pytz.timezone('Asia/Taipei'))
                    prefix = "TW" if 6 <= now_tpe.hour <= 18 else "US"
                    send_telegram_message(f"🎯{prefix} | 🟡暫停監測")
                    
        if st.session_state.monitoring: st.success("🟢 即時監測中")
        else: st.info("🟡 監測暫停中")

    with st.container(border=True):
        sidebar_header("➕", "新增即時監控")
        market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_a")
        
        if "台灣" in market_choice:
            selected_db = st.selectbox("tw 資料庫選取", tw_options, format_func=format_tw_option, key="sel_tw_val", on_change=on_sel_change)
        else:
            selected_db = st.selectbox("us 資料庫選取", us_options, format_func=lambda x: stock_dict.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_us_val", on_change=on_sel_change)
            
        if st.session_state.clear_input_flag:
            st.session_state.manual_sym_val = ""
            st.session_state.clear_input_flag = False
            
        new_sym = st.text_input("或 手動輸入代碼", placeholder="例: 6531", key="manual_sym_val", on_change=on_manual_change).strip().upper()
        
        st.markdown("<div style='font-size:0.85rem; color:#94a3b8; margin-bottom:5px;'>監控條件設定：</div>", unsafe_allow_html=True)
        th_text = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_a", label_visibility="collapsed")
        entry_text = st.text_input("進場提醒 ($)", value="", placeholder="進場價 (例: 150)", key="entry_a", label_visibility="collapsed")
        exit_text = st.text_input("出場提醒 ($)", value="", placeholder="出場價 (例: 190)", key="exit_a", label_visibility="collapsed")
        
        if st.button("確認新增", use_container_width=True, key="btn_add_a"):
            if not (th_text.strip() or entry_text.strip() or exit_text.strip()):
                st.warning("⚠️ 請至少輸入一項監控條件！")
            else:
                target_sym = new_sym if new_sym else (selected_db if selected_db != "--- 請選擇 ---" else None)
                if target_sym:
                    mkt = "tw" if "台灣" in market_choice else "us"
                    if mkt == "tw" and not target_sym.endswith(".TW"): target_sym += ".TW"
                    if mkt == "us": target_sym = target_sym.replace(".TW", "")
                    
                    display_name = ""
                    is_valid = False
                    
                    with st.spinner(f"🔍 驗證標的與獲取名稱中..."):
                        try:
                            if mkt == "tw":
                                res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_sym}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                                soup = BeautifulSoup(res.text, 'html.parser')
                                title = soup.find('title').text
                                if " - " in title:
                                    clean_title = title.split(" - ")[0].split("(")[0]
                                    name_part = clean_title.replace(target_sym.replace('.TW', ''), '').strip()
                                    if name_part: display_name = name_part; is_valid = True
                            else:
                                fi = yf.Ticker(target_sym).fast_info
                                if fi.last_price is not None: display_name = target_sym; is_valid = True
                        except: pass
                    
                    if is_valid:
                        if target_sym not in stock_dict or stock_dict[target_sym] != display_name:
                            stock_dict[target_sym] = display_name
                            save_stock_dict(stock_dict)
                        db_manager.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                        st.cache_data.clear()
                        st.session_state.clear_input_flag = True
                        st.success(f"✅ {display_name} ({target_sym}) 新增成功！")
                        st.rerun()
                    else: st.error("❌ 查無此股票或獲取失敗，拒絕寫入！")

    with st.container(border=True):
        sidebar_header("🗑️", "移除監測標的")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=lambda x: monitor_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_a", label_visibility="collapsed")
        if st.button("確認刪除", use_container_width=True, key="btn_del_a"):
            if del_sym != "--- 請選擇 ---":
                db_manager.remove_monitor_item(del_sym)
                st.cache_data.clear()
                st.success(f"🗑️ 已移除標的")
                st.rerun()

    with st.container(border=True):
        sidebar_header("⏱️", "系統運行狀態")
        refresh_sec_a = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_a")
        if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_a"): 
            st.cache_data.clear()
            st.rerun()

# ==========================================================
# 2️⃣ 手動推播測試元件
# ==========================================================
def render_telegram_manual_test_ui():
    with st.sidebar.expander("🛠️ 系統推播測試", expanded=False):
        if st.button("發送 Telegram 測試", use_container_width=True):
            try:
                send_telegram_message("🔔 來自 QBS 系統的推播測試！")
                st.success("✅ 發送成功！")
            except Exception as e:
                st.error(f"發送失敗: {e}")

# ==========================================================
# 3️⃣ 主畫面戰情室 (含 TW/US 分組與精美 HTML 小卡排版)
# ==========================================================
def render_radar_dashboard():
    is_monitoring = st.session_state.get("monitoring", False)
    
    # 呼叫心跳引擎獲取最新報價與觸發警報
    quotes, alerts = engine_monitor.run_radar_scan(is_monitoring=is_monitoring)
    
    # 若有觸發警報，顯示在畫面上方
    if alerts:
        for alert in alerts:
            st.warning(f"【{alert['ticker']}】 {alert['type']} : {alert['message']}")
            
    # 取得資料庫中所有監控標的
    monitor_items = db_manager.get_all_monitor_items()
    if not monitor_items:
        st.info("💡 目前雷達無監控標的，請從左側邊欄新增。")
        return
        
    # 區分台股與美股
    tw_items = [item for item in monitor_items if item.get('market') == 'tw' or '.TW' in item['ticker']]
    us_items = [item for item in monitor_items if item.get('market'] == 'us' and '.TW' not in item['ticker']]
    
    def render_market_group(title, icon, market_type, items):
        if not items:
            return
            
        st.markdown(f"### {icon} {title}")
        
        # 顯示大盤指數卡片
        index_ticker = '^TWII' if market_type == 'tw' else '^IXIC'
        index_name = '台灣加權指數' if market_type == 'tw' else '那斯達克指數'
        
        idx_cols = st.columns(4)
        with idx_cols[0]:
            if index_ticker in quotes:
                q = quotes[index_ticker]
                price = q['current']
                change = q['change_pct']
                color_hex = "#ef4444" if change < 0 else ("#10b981" if change > 0 else "#94a3b8")
                sign = "+" if change > 0 else ""
                
                idx_html = textwrap.dedent(f"""
                <div style="background-color: #0f172a; padding: 14px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 12px;">
                    <div style="color: #60a5fa; font-size: 0.8rem; font-weight: 700; margin-bottom: 2px;">{index_ticker} (大盤指標)</div>
                    <div style="color: #f8fafc; font-size: 1.05rem; font-weight: 700; margin-bottom: 8px;">{index_name}</div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div style="color: #e2e8f0; font-size: 1.25rem; font-weight: 800;">${price:,.2f}</div>
                        <div style="color: {color_hex}; font-size: 0.85rem; font-weight: 700; background-color: {color_hex}20; padding: 2px 6px; border-radius: 4px;">{sign}{change}%</div>
                    </div>
                </div>
                """).strip()
                st.markdown(idx_html, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: #0f172a; padding: 14px; border-radius: 10px; border: 1px dashed #3b82f6; margin-bottom: 12px;">
                    <div style="color: #60a5fa; font-size: 0.8rem; font-weight: 700;">{index_ticker}</div>
                    <div style="color: #f8fafc; font-size: 1.05rem; font-weight: 700; margin-bottom: 8px;">{index_name}</div>
                    <div style="color: #64748b; font-size: 0.85rem;">⏳ 大盤載入中...</div>
                </div>
                """, unsafe_allow_html=True)
                
        # 渲染個股小卡網格
        cols = st.columns(4)
        for i, item in enumerate(items):
            ticker = item['ticker']
            name = item.get('display_name', ticker)
            
            # 智慧清理股票名稱重複顯示問題
            clean_ticker = ticker.replace('.TW', '')
            if name.startswith(clean_ticker):
                display_title = name
            else:
                display_title = f"{clean_ticker} {name}"
                
            target_col = cols[(i + 1) % 4]
            
            if ticker in quotes:
                q = quotes[ticker]
                price = q['current']
                change = q['change_pct']
                
                color_hex = "#ef4444" if change < 0 else ("#10b981" if change > 0 else "#94a3b8")
                bg_opacity = "20"
                sign = "+" if change > 0 else ""
                
                card_html = textwrap.dedent(f"""
                <div style="background-color: #1e293b; padding: 16px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 4px;">{ticker}</div>
                    <div style="color: #f8fafc; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                        <div style="color: #e2e8f0; font-size: 1.35rem; font-weight: 800; letter-spacing: 0.5px;">${price}</div>
                        <div style="color: {color_hex}; font-size: 0.95rem; font-weight: 700; background-color: {color_hex}{bg_opacity}; padding: 3px 8px; border-radius: 6px;">{sign}{change}%</div>
                    </div>
                </div>
                """).strip()
                target_col.markdown(card_html, unsafe_allow_html=True)
            else:
                loading_html = textwrap.dedent(f"""
                <div style="background-color: #1e293b; padding: 16px; border-radius: 10px; border: 1px dashed #475569; margin-bottom: 12px;">
                    <div style="color: #64748b; font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;">{ticker}</div>
                    <div style="color: #94a3b8; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px;">{display_title}</div>
                    <div style="color: #475569; font-size: 0.95rem; font-style: italic;">⏳ 報價載入中...</div>
                </div>
                """).strip()
                target_col.markdown(loading_html, unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)

    # 依序渲染台股與美股分組戰情室
    render_market_group("台灣股市戰情室", "🇹🇼", "tw", tw_items)
    render_market_group("美國股市戰情室", "🇺🇸", "us", us_items)
