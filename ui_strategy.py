# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_strategy.py
# 程式版本 : ui_v1.3.7 (Phase 7: 雲端動態字典全面取代版)
#
# 📋 進版說明 (Version Notes):
#   1. [字典上雲] 拋棄傳入的本地 JSON 參數，改從 Neon 資料庫動態載入選單項目。
#   2. [格式統一] 實作 dynamic_format_option，讓資料庫選取與刪除選單全面對齊「代碼 + 名稱」。
#   3. [永久儲存] 新增標的時同步寫入雲端字典，徹底解決 Streamlit 重開資料消失問題。
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
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
from core.repositories.market_repository import market_repo

# ==========================================================
# 1️⃣ 側邊欄渲染 (包含雲端字典覆寫機制)
# ==========================================================
def render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header):
    if "sel_tw_val_b" not in st.session_state: st.session_state.sel_tw_val_b = "--- 請選擇 ---"
    if "sel_us_val_b" not in st.session_state: st.session_state.sel_us_val_b = "--- 請選擇 ---"
    if "manual_sym_val_b" not in st.session_state: st.session_state.manual_sym_val_b = ""
    if "clear_input_flag_b" not in st.session_state: st.session_state.clear_input_flag_b = False
    
    if "failed_tickers_b" not in st.session_state: st.session_state.failed_tickers_b = []

    def on_sel_change_b(): 
        st.session_state.manual_sym_val_b = ""
        
    def on_manual_change_b():
        if st.session_state.manual_sym_val_b.strip() != "":
            st.session_state.sel_tw_val_b = "--- 請選擇 ---"
            st.session_state.sel_us_val_b = "--- 請選擇 ---"

    if st.session_state.clear_input_flag_b:
        st.session_state.manual_sym_val_b = ""
        st.session_state.sel_tw_val_b = "--- 請選擇 ---"
        st.session_state.sel_us_val_b = "--- 請選擇 ---"
        st.session_state.clear_input_flag_b = False

    # 🔥 關鍵改造：從 Neon 資料庫載入雲端股票字典，覆寫原有的暫存參數
    db_tw_items = market_repo.get_dict_options('tw')
    db_us_items = market_repo.get_dict_options('us')
    
    # 建立雲端字典映射表供下拉選單格式化使用
    db_dict_map = {item['ticker']: item['display_name'] for item in db_tw_items + db_us_items}
    
    dynamic_tw_options = ["--- 請選擇 ---"] + [item['ticker'] for item in db_tw_items]
    dynamic_us_options = ["--- 請選擇 ---"] + [item['ticker'] for item in db_us_items]

    def dynamic_format_option(ticker):
        """通用格式化函數：統一資料庫選取下拉選單的顯示格式"""
        if ticker == "--- 請選擇 ---":
            return ticker
        clean_ticker = ticker.replace('.TW', '')
        name = str(db_dict_map.get(ticker, "")).strip()
        if not name or name == ticker or name == clean_ticker: return clean_ticker
        if name.startswith(clean_ticker): return name
        return f"{clean_ticker} {name}"

    backtest_items = strategy_repo.get_all_backtest_items()
    backtest_tickers = [item['ticker'] for item in backtest_items]
    backtest_map = {item['ticker']: item['display_name'] for item in backtest_items}
    
    def format_del_option(ticker):
        """刪除選單專用格式化函數"""
        if ticker == "--- 請選擇 ---":
            return ticker
        clean_ticker = ticker.replace('.TW', '')
        name = str(backtest_map.get(ticker, "")).strip()
        if not name or name == ticker or name == clean_ticker: return clean_ticker
        if name.startswith(clean_ticker): return name
        return f"{clean_ticker} {name}"
    
    with st.container(border=True):
        sidebar_header("🧪", "回測策略設定")
        strategy = st.selectbox("選擇策略", ["趨勢動能策略 (Trend Momentum)", "均值回歸策略 (待開發)"], label_visibility="collapsed")
        
    with st.container(border=True):
        sidebar_header("➕", "新增回測標的")
        market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_b")
        
        # 替換為動態雲端字典與統一的格式化函數
        if "台灣" in market_choice:
            selected_db_b = st.selectbox("tw 資料庫選取", dynamic_tw_options, format_func=dynamic_format_option, key="sel_tw_val_b", on_change=on_sel_change_b)
        else:
            selected_db_b = st.selectbox("us 資料庫選取", dynamic_us_options, format_func=dynamic_format_option, key="sel_us_val_b", on_change=on_sel_change_b)
            
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

                # 相容性保留：寫入舊版本地字典，避免其他依賴模組報錯
                if target_sym_b not in stock_dict or stock_dict[target_sym_b] != display_name:
                    stock_dict[target_sym_b] = display_name
                    save_stock_dict(stock_dict)

                # 🔥 關鍵寫入：永久寫入 Neon 雲端字典與回測母體表
                market_repo.upsert_dict_item(target_sym_b, display_name, mkt)
                strategy_repo.add_backtest_item(target_sym_b, market=mkt, display_name=display_name)
                
                if target_sym_b in st.session_state.failed_tickers_b:
                    st.session_state.failed_tickers_b.remove(target_sym_b)
                    
                st.session_state.clear_input_flag_b = True
                st.success(f"✅ {target_sym_b} 加入回測池並永久建檔！")
                time.sleep(0.5) 
                st.rerun()
            else: 
                st.warning("⚠️ 請選擇或輸入標的代碼！")
                
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
                    if t in st.session_state.failed_tickers_b:
                        st.session_state.failed_tickers_b.remove(t)
                st.success(f"✅ 已寫入 {len(tickers_to_add)} 檔！")
                st.rerun()

    with st.container(border=True):
        sidebar_header("🗑️", "移除回測標的")
        del_sym = st.selectbox(
            "刪除目標", 
            ["--- 請選擇 ---"] + backtest_tickers, 
            format_func=format_del_option, 
            key="del_b", 
            label_visibility="collapsed"
        )
        if st.button("確認刪除", use_container_width=True, key="btn_del_b"):
            if del_sym != "--- 請選擇 ---":
                strategy_repo.remove_backtest_item(del_sym)
                st.success("🗑️ 移除成功")
                st.rerun()

    with st.container(border=True):
        sidebar_header("📥", "歷史資料管理")
        if st.button("🔄 5 年資料", use_container_width=True):
            if not backtest_tickers: 
                st.warning("⚠️ 回測池目前為空")
            else:
                st.write("📊 **更新進度：**")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success, failed_list = data_fetcher.smart_update_historical_data(
                    tickers=backtest_tickers, 
                    force_5y=True,
                    progress_bar=progress_bar,
                    status_text=status_text
                )
                st.session_state.failed_tickers_b = failed_list
                
                if success: 
                    status_text.success("🎉 所有標的更新完成！畫面即將重整...")
                else: 
                    status_text.error(f"⚠️ 結束作業。有 {len(failed_list)} 檔標的更新失敗。")
                    
                time.sleep(2.0) 
                st.rerun()     

    with st.container(border=True):
        sidebar_header("⏱️", "系統運行狀態")
        refresh_min_b = st.slider("刷新頻率(分)", 1, 60, 5, key="refresh_min_ui_b")
        st.session_state.refresh_b = refresh_min_b * 60 
        
        if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_b"): st.rerun()

# ==========================================================
# 2️⃣ 單張股票戰情小卡渲染 (HTML 生成)
# ==========================================================
def render_stock_card_html(row, failed_tickers):
    ticker = row['代碼']
    clean_ticker = ticker.replace('.TW', '')
    clean_name = str(row['名稱']).strip()

    if not clean_name or clean_name == ticker or clean_name == clean_ticker:
        display_title = clean_ticker
    elif clean_name.startswith(clean_ticker):
        display_title = clean_name
    else:
        display_title = f"{clean_ticker} {clean_name}"

    total_score = row['總分']

    if total_score == -1:
        if ticker in failed_tickers:
            card_html = f"""<div style="width: 280px; min-width: 280px; background-color: #2b1819; border: 1px solid #7f1d1d; border-radius: 8px; padding: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between;">
<div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
<div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 4px;">目前狀態</div>
<div style="font-size: 1.25rem; font-weight: 700; color: #ef4444; margin-bottom: 20px;">🔴 資料抓取失敗</div>
<div style="font-size: 0.85rem; color: #94a3b8; font-style: italic; border-top: 1px solid #450a0a; padding-top: 10px;">請稍後重試，或確認代碼無誤</div>
</div>"""
        else:
            card_html = f"""<div style="width: 280px; min-width: 280px; background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between;">
<div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
<div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600; margin-bottom: 4px;">目前狀態</div>
<div style="font-size: 1.3rem; font-weight: 700; color: #fbbf24; margin-bottom: 20px;">⏳ 未建檔 (等待資料)</div>
<div style="font-size: 0.85rem; color: #64748b; font-style: italic; border-top: 1px solid #334155; padding-top: 10px;">請點擊左側「強制更新」按鈕</div>
</div>"""
        return card_html

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
# 3️⃣ 頁面 B 市場分區渲染
# ==========================================================
def render_market_group_html(market_type, targets_df, failed_tickers):
    if targets_df.empty:
        return ""
        
    if market_type == "tw":
        idx_name = "tw 台灣股市 (Taiwan Market)"
        icon = "🔴"
    else:
        idx_name = "us 美國股市 (Nasdaq / NYSE)"
        icon = "🟢"
        
    bar_color = "#3b82f6"
    
    header_html = f"""<div style="display: flex; align-items: center; margin: 30px 0 20px 0;">
<div style="width: 4px; height: 22px; background-color: {bar_color}; margin-right: 12px;"></div>
<div style="font-size: 1.25rem; font-weight: 800; color: #f8fafc;">
{icon} {idx_name}
</div>
</div>"""

    cards_html = "<div style='display: flex; flex-wrap: wrap; gap: 18px;'>"
    for _, row in targets_df.iterrows():
        cards_html += render_stock_card_html(row, failed_tickers)
    cards_html += "</div>"
    
    return header_html + cards_html

# ==========================================================
# 4️⃣ 頁面 B 回測戰情室主程式
# ==========================================================
def render_backtest_dashboard():
    st.markdown("### 🎯 策略回測戰情室 (The Research Hub)")
    
    failed_tickers = st.session_state.get("failed_tickers_b", [])
    
    with st.spinner("🧠 核心引擎運算中，正在掃描技術指標與背離訊號..."):
        result_df = engine_core.run_trend_momentum_analysis()
        
    if result_df.empty:
        st.warning("⚠️ 尚無回測結果，請確認左側「回測母體」是否有新增股票，並已下載歷史資料。")
        return
        
    pass_count = len(result_df[result_df['總分'] >= 45])
    unbuilt_count = len(result_df[result_df['總分'] == -1])
    failed_count = len([t for t in failed_tickers if t in result_df['代碼'].values])
    
    info_msg = f"💡 運算完成！共分析 **{len(result_df)}** 檔標的，其中有 **{pass_count}** 檔突破 45 分強勢門檻。"
    if unbuilt_count > 0:
        waiting_count = unbuilt_count - failed_count
        if waiting_count > 0:
            info_msg += f" (目前有 **{waiting_count}** 檔標的等待下載歷史資料)"
        if failed_count > 0:
            info_msg += f" (⚠️ 有 **{failed_count}** 檔標的資料抓取失敗)"
            
    st.info(info_msg)
    
    tw_df = result_df[result_df['代碼'].str.endswith('.TW')]
    us_df = result_df[~result_df['代碼'].str.endswith('.TW')]
    
    final_html = ""
    
    if not tw_df.empty:
        final_html += render_market_group_html("tw", tw_df, failed_tickers)
        
    if not us_df.empty:
        if not tw_df.empty:
            final_html += "<div style='height: 10px;'></div>" 
        final_html += render_market_group_html("us", us_df, failed_tickers)
        
    st.markdown(final_html, unsafe_allow_html=True)
