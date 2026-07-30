import streamlit as st
import os
import json
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from core import db_manager
from core import data_fetcher

def render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header):
    if "sel_tw_val_b" not in st.session_state: st.session_state.sel_tw_val_b = "--- 請選擇 ---"
    if "sel_us_val_b" not in st.session_state: st.session_state.sel_us_val_b = "--- 請選擇 ---"
    if "manual_sym_val_b" not in st.session_state: st.session_state.manual_sym_val_b = ""
    if "clear_input_flag_b" not in st.session_state: st.session_state.clear_input_flag_b = False

    def on_sel_change_b(): st.session_state.manual_sym_val_b = ""
    def on_manual_change_b():
        if st.session_state.manual_sym_val_b.strip() != "":
            st.session_state.sel_tw_val_b = "--- 請選擇 ---"
            st.session_state.sel_us_val_b = "--- 請選擇 ---"

    backtest_items = db_manager.get_all_backtest_items()
    backtest_tickers = [item['ticker'] for item in backtest_items]
    backtest_map = {item['ticker']: item['display_name'] for item in backtest_items}
    
    with st.container(border=True):
        sidebar_header("🧪", "回測策略設定")
        strategy = st.selectbox("選擇策略", ["趨勢動能策略 (Trend Momentum)", "均值回歸策略 (待開發)"], label_visibility="collapsed")
        
    with st.container(border=True):
        sidebar_header("➕", "新增回測標的")
        market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_b")
        
        if "台灣" in market_choice:
            selected_db_b = st.selectbox("tw 資料庫選取", tw_options, format_func=format_tw_option, key="sel_tw_val_b", on_change=on_sel_change_b)
        else:
            selected_db_b = st.selectbox("us 資料庫選取", us_options, format_func=lambda x: stock_dict.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_us_val_b", on_change=on_sel_change_b)
            
        if st.session_state.clear_input_flag_b:
            st.session_state.manual_sym_val_b = ""
            st.session_state.clear_input_flag_b = False

        new_sym_b = st.text_input("或 手動輸入代碼", placeholder="例: AAPL 或 2330", key="manual_sym_val_b", on_change=on_manual_change_b).strip().upper()
        
        if st.button("確認新增", use_container_width=True, key="btn_add_b"):
            target_sym_b = new_sym_b if new_sym_b else (selected_db_b if selected_db_b != "--- 請選擇 ---" else None)
            if target_sym_b:
                mkt = "tw" if "台灣" in market_choice else "us"
                if mkt == "tw" and not target_sym_b.endswith(".TW"): target_sym_b += ".TW"
                if mkt == "us": target_sym_b = target_sym_b.replace(".TW", "")

                display_name = target_sym_b
                with st.spinner("🔍 寫入標的與同步字典中..."):
                    try:
                        if mkt == "tw":
                            res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_sym_b}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                            soup = BeautifulSoup(res.text, 'html.parser')
                            title = soup.find('title').text
                            if " - " in title:
                                clean_title = title.split(" - ")[0].split("(")[0]
                                name_part = clean_title.replace(target_sym_b.replace('.TW', ''), '').strip()
                                if name_part: display_name = name_part
                        else:
                            fi = yf.Ticker(target_sym_b).fast_info
                            if fi.last_price is not None: display_name = target_sym_b
                    except: pass

                if target_sym_b not in stock_dict or stock_dict[target_sym_b] != display_name:
                    stock_dict[target_sym_b] = display_name
                    save_stock_dict(stock_dict)

                db_manager.add_backtest_item(target_sym_b, market=mkt)
                st.session_state.clear_input_flag_b = True
                st.success(f"✅ {target_sym_b} 加入回測池！")
                st.rerun()
            else: st.warning("⚠️ 請選擇或輸入標的代碼！")
                
    with st.container(border=True):
        sidebar_header("🗂️", "族群批次輸入")
        sector_options = ["--- 請選擇 ---"]
        sectors_data = {}
        
        # 動態抓取根目錄 (確保不被模組位置影響)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        sector_file = os.path.join(BASE_DIR, "config", "sectors.json")
        if os.path.exists(sector_file):
            with open(sector_file, "r", encoding="utf-8") as f:
                try:
                    sectors_data = json.load(f)
                    sector_options.extend(list(sectors_data.keys()))
                except Exception: pass
        
        selected_sector = st.selectbox("選擇族群", sector_options, key="sector_sel", label_visibility="collapsed")
        if st.button("批次寫入", use_container_width=True, key="btn_sector_add"):
            if selected_sector != "--- 請選擇 ---":
                tickers_to_add = sectors_data.get(selected_sector, [])
                for t in tickers_to_add:
                    mkt = "tw" if ".TW" in t else "us"
                    db_manager.add_backtest_item(t, market=mkt)
                st.success(f"✅ 已寫入 {len(tickers_to_add)} 檔！")
                st.rerun()

    with st.container(border=True):
        sidebar_header("🗑️", "移除回測標的")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + backtest_tickers, format_func=lambda x: backtest_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_b", label_visibility="collapsed")
        if st.button("確認刪除", use_container_width=True, key="btn_del_b"):
            if del_sym != "--- 請選擇 ---":
                db_manager.remove_backtest_item(del_sym)
                st.success("🗑️ 移除成功")
                st.rerun()

    with st.container(border=True):
        sidebar_header("📥", "歷史資料管理")
        if st.button("強制更新 5 年歷史資料", use_container_width=True):
            if not backtest_tickers: st.warning("⚠️ 回測池目前為空")
            else:
                with st.spinner('🔄 請求 K 線資料...'):
                    success = data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True)
                    if success: st.success("✅ 更新完成！")
                    else: st.error("⚠️ 更新失敗")

    with st.container(border=True):
        sidebar_header("⏱️", "系統運行狀態")
        refresh_sec_b = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_b")
        if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_b"): st.rerun()
