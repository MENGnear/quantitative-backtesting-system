import streamlit as st
import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from core import db_manager
from services.telegram_service import send_telegram_message

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
