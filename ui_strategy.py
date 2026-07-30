# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_strategy.py
# 程式版本 : ui_v1.2.1 (Pre-Phase 7: 微前端側邊欄解耦修復版)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 導入 render_sidebar，承接從 QBS_app 剝離的回測專屬側邊欄邏輯。
#   2. [領域隔離] 將「族群批次寫入」與「5 年歷史資料更新」等動作收斂於此模組。
#   3. [復原修復] 完整保留原版 v1.0.0 中您設計的「分數門檻高光」、「底背離標籤」與「4 欄並排動態網格」UI。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 側邊欄渲染 (Micro-Frontend)
#   - 2️⃣ 單張股票戰情小卡渲染 (維持原樣)
#   - 3️⃣ 頁面 B 回測戰情室主程式 (維持原樣)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import pandas as pd
import os
import json
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from core import db_manager
from core import engine_core
from core import data_fetcher

# ==========================================================
# 1️⃣ 側邊欄渲染 (Micro-Frontend)
# ==========================================================
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

# ==========================================================
# 2️⃣ 單張股票戰情小卡渲染
# ==========================================================
def render_stock_card(row):
    """渲染單張股票戰情小卡 (HTML/CSS)"""
    total_score = row['總分']
    if total_score >= 45:
        score_color = "#10b981" 
    elif total_score >= 30:
        score_color = "#fbbf24" 
    else:
        score_color = "#ef4444" 
        
    divergence_tag = ""
    if row['底背離'] == '✅':
        divergence_tag = "<span style='background-color:#7c3aed; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold; margin-left:8px;'>🚨 底背離</span>"

    card_html = f"""
    <div style="padding: 10px; display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">
                {row['代碼']} <span style="font-size: 0.9rem; color: #94a3b8;">{row['名稱']}</span>
            </div>
            {divergence_tag}
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #334155; padding-bottom: 8px;">
            <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600;">策略總分</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: {score_color}; line-height: 1;">
                {int(total_score)}<span style="font-size: 1rem; color: #64748b; font-weight: 600;">/80</span>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 6px; font-size: 0.85rem;">
            <div style="color: #cbd5e1;">收盤價：<span style="color: #f8fafc; font-weight: 600;">${row['收盤價']:.2f}</span></div>
            <div style="color: #cbd5e1;">RSI_14：<span style="color: #f8fafc; font-weight: 600;">{row['RSI_14']:.1f}</span></div>
            <div style="color: #94a3b8; font-size: 0.8rem;">趨勢(60)：<span style="color: #cbd5e1;">{int(row['趨勢分(60)'])}</span></div>
            <div style="color: #94a3b8; font-size: 0.8rem;">紅利(20)：<span style="color: #cbd5e1;">{int(row['紅利分(20)'])}</span></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ==========================================================
# 3️⃣ 頁面 B 回測戰情室主程式
# ==========================================================
def render_backtest_dashboard():
    """負責頁面 B 的整體回測戰情室渲染"""
    st.markdown("### 🎯 策略回測戰情室 (The Research Hub)")
    
    with st.spinner("🧠 核心引擎運算中，正在掃描技術指標與背離訊號..."):
        # 呼叫核心大腦取得算好的 DataFrame
        result_df = engine_core.run_trend_momentum_analysis()
        
    if result_df.empty:
        st.warning("⚠️ 尚無回測結果，請確認左側「回測母體」是否有新增股票，並已下載歷史資料。")
        return
        
    # 計算及格檔數
    pass_count = len(result_df[result_df['總分'] >= 45])
    st.info(f"💡 運算完成！共分析 **{len(result_df)}** 檔標的，其中有 **{pass_count}** 檔突破 45 分強勢門檻。")
    
    # 建立動態網格 (每排 4 欄)
    cols_per_row = 4
    for i in range(0, len(result_df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(result_df):
                row_data = result_df.iloc[i + j]
                with cols[j]:
                    with st.container(border=True):
                        render_stock_card(row_data)
