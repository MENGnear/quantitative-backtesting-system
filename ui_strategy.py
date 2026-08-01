# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_strategy.py
# 程式版本 : ui_v1.2.7 (Phase 7: 卡片標題邏輯完美對齊版)
#
# 📋 進版說明 (Version Notes):
#   1. [顯示修復] 100% 移植 ui_monitor.py 的卡片標題過濾邏輯 (拔除 .TW、防範 NVDA NVDA 重複)。
#   2. [視覺統一] 維持 Flexbox 動態網格與卡片 CSS (280px 寬度、陰影、字體層級)。
#   3. [體驗優化] 強制下載完成後自動重整畫面。
#   4. [架構重構] 完全對接 engines.strategy 與 strategy_repo。
# ==========================================================

import streamlit as st
import pandas as pd
import os
import json
import requests
import time
from bs4 import BeautifulSoup
import yfinance as yf
from core.repositories.strategy_repository import strategy_repo
from engines import strategy as engine_core
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

    backtest_items = strategy_repo.get_all_backtest_items()
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

                strategy_repo.add_backtest_item(target_sym_b, market=mkt, display_name=display_name)
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
                    strategy_repo.add_backtest_item(t, market=mkt)
                st.success(f"✅ 已寫入 {len(tickers_to_add)} 檔！")
                st.rerun()

    with st.container(border=True):
        sidebar_header("🗑️", "移除回測標的")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + backtest_tickers, format_func=lambda x: backtest_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_b", label_visibility="collapsed")
        if st.button("確認刪除", use_container_width=True, key="btn_del_b"):
            if del_sym != "--- 請選擇 ---":
                strategy_repo.remove_backtest_item(del_sym)
                st.success("🗑️ 移除成功")
                st.rerun()

    with st.container(border=True):
        sidebar_header("📥", "歷史資料管理")
        if st.button("強制更新 5 年歷史資料", use_container_width=True):
            if not backtest_tickers: st.warning("⚠️ 回測池目前為空")
            else:
                with st.spinner('🔄 請求 K 線資料...'):
                    success = data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True)
                    if success: 
                        st.success("✅ 更新完成！正在重整畫面...")
                        time.sleep(1)  
                        st.rerun()     
                    else: 
                        st.error("⚠️ 更新失敗")

    with st.container(border=True):
        sidebar_header("⏱️", "系統運行狀態")
        refresh_sec_b = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_b")
        if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_b"): st.rerun()

# ==========================================================
# 2️⃣ 單張股票戰情小卡渲染 (HTML 生成)
# ==========================================================
def render_stock_card_html(row):
    """回傳單張股票戰情小卡的 HTML 原始碼 (與 ui_monitor 像素級對齊)"""
    total_score = row['總分']
    
    # 根據分數給予對應的底色與邊框
    if total_score >= 45:
        bg_color = "#18241d"
        border_color = "#1f4738"
        score_color = "#10b981"
    elif total_score >= 30:
        bg_color = "#2a2110" 
        border_color = "#4d3810"
        score_color = "#fbbf24"
    else:
        bg_color = "#2b1819"
        border_color = "#5a262c"
        score_color = "#ef4444"
        
    divergence_badge = ""
    if row['底背離'] == '✅':
        divergence_badge = """<div style='margin-top: 15px; background-color: #2e1065; color: #d8b4fe; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 0.95rem; border: 1px solid #9333ea; box-shadow: inset 0 0 8px rgba(0,0,0,0.5);'>🚨 發現底背離訊號</div>"""

    # 🔥 完美移植 ui_monitor.py 的名稱過濾邏輯
    ticker = row['代碼']
    clean_ticker = ticker.replace('.TW', '')
    clean_name = str(row['名稱']).strip()

    if not clean_name or clean_name == ticker or clean_name == clean_ticker:
        display_title = clean_ticker
    elif clean_name.startswith(clean_ticker):
        display_title = clean_name
    else:
        display_title = f"{clean_ticker} {clean_name}"

    card_html = f"""<div style="width: 280px; min-width: 280px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between;">
<div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
<div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 4px;">策略總分</div>
<div style="font-size: 2.1rem; font-weight: 800; color: {score_color}; margin-bottom: 16px;">{int(total_score)}<span style="font-size: 1.1rem; color: #64748b; font-weight: 600; margin-left: 4px;">/80</span></div>
<div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px;">
<div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">收盤價： <span style="color: #f8fafc; margin-left: 5px;">${row['收盤價']:.2f}</span></div>
<div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">RSI (14)： <span style="color: #f8fafc; margin-left: 5px;">{row['RSI_14']:.1f}</span></div>
<div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">趨勢分 (60)： <span style="color: #cbd5e1; margin-left: 5px;">{int(row['趨勢分(60)'])}</span></div>
<div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">紅利分 (20)： <span style="color: #cbd5e1; margin-left: 5px;">{int(row['紅利分(20)'])}</span></div>
</div>
{divergence_badge}
</div>"""
    return card_html

# ==========================================================
# 3️⃣ 頁面 B 回測戰情室主程式
# ==========================================================
def render_backtest_dashboard():
    """負責頁面 B 的整體回測戰情室渲染"""
    st.markdown("### 🎯 策略回測戰情室 (The Research Hub)")
    
    with st.spinner("🧠 核心引擎運算中，正在掃描技術指標與背離訊號..."):
        result_df = engine_core.run_trend_momentum_analysis()
        
    if result_df.empty:
        st.warning("⚠️ 尚無回測結果，請確認左側「回測母體」是否有新增股票，並已下載歷史資料。")
        return
        
    pass_count = len(result_df[result_df['總分'] >= 45])
    st.info(f"💡 運算完成！共分析 **{len(result_df)}** 檔標的，其中有 **{pass_count}** 檔突破 45 分強勢門檻。")
    
    cards_html = "<div style='display: flex; flex-wrap: wrap; gap: 18px;'>"
    
    for _, row in result_df.iterrows():
        cards_html += render_stock_card_html(row)
        
    cards_html += "</div>"
    
    st.markdown(cards_html, unsafe_allow_html=True)
