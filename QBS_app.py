# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v4.1.3 (Phase 4.1: 極端名稱淨化版)
#
# 📋 進版說明 (Version Notes):
#   1. [錯誤修復] 強化奇摩股市爬蟲字串處理，使用括號強制截斷，確保絕對不會存入「(.TW) 走勢圖」。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置
#   - 2️⃣ 動態載入外部深色視覺 CSS 樣板
#   - 3️⃣ 系統全域常數與資料庫初始化
#   - 4️⃣ 側邊欄控制面板 (🔥 V4.1.3 局部修正：極端字串淨化)
#   - 5️⃣ 主畫面戰情室
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz
import os
import json
import sqlite3
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from core import db_manager
from core import data_fetcher
import ui_strategy
import ui_monitor

# ==========================================================
# 1️⃣ 頁面設定與全域配置
# ==========================================================
st.set_page_config(
    page_title="QBS 量化回測系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# 2️⃣ 動態載入外部深色視覺 CSS 樣板
# ==========================================================
def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(os.path.join("assets", "style.css"))

# ==========================================================
# 3️⃣ 系統全域常數與資料庫/Session 初始化
# ==========================================================
APP_VERSION = "QBS_v4.1.3"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

test_display_map = {
    "2330.TW": "2330 台積電",
    "2454.TW": "2454 聯發科",
    "AAPL": "AAPL 蘋果",
    "NVDA": "NVDA 輝達"
}

# ==========================================================
# 4️⃣ 側邊欄控制面板 (🔥 動態智能切換)
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        st.markdown("### 🧭 系統導航")
        current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], label_visibility="collapsed", key="main_page_nav")
    
    # ==========================================
    # 🌟 頁面 A 專屬側邊欄 (Monitor)
    # ==========================================
    if current_page == "📡 頁面 A : 即時雷達監測":
        monitor_items = db_manager.get_all_monitor_items()
        monitor_tickers = [item['ticker'] for item in monitor_items]
        monitor_map = {item['ticker']: f"{item['ticker']} {item['display_name']}" for item in monitor_items}
        
        with st.container(border=True):
            st.markdown("### ▶️ 執行股票監測")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("開始", use_container_width=True, key="start_mon"): st.session_state.monitoring = True
            with col_btn2:
                if st.button("暫停", use_container_width=True, key="stop_mon"): st.session_state.monitoring = False
                    
            if st.session_state.monitoring: st.success("🟢 系統即時監測中...")
            else: st.info("🟡 監測暫停中")
            
        with st.container(border=True):
            st.markdown("### ➕ 新增實戰監控 (需設警報)")
            market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_a")
            
            if "台灣" in market_choice:
                selected_db = st.selectbox("tw 資料庫選取", ["--- 請選擇 ---", "2330.TW", "2454.TW"], format_func=lambda x: test_display_map.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_tw_a")
            else:
                selected_db = st.selectbox("us 資料庫選取", ["--- 請選擇 ---", "AAPL", "NVDA"], format_func=lambda x: test_display_map.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_us_a")
                
            new_sym = st.text_input("或 手動輸入代碼", value="", placeholder="例: 6531", key="sym_manual_a").strip().upper()
            th_text = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_a")
            entry_text = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200", key="entry_a")
            exit_text = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190", key="exit_a")
            
            if st.button("確認新增至監測池", use_container_width=True, key="btn_add_a"):
                target_sym = new_sym if new_sym else (selected_db if selected_db != "--- 請選擇 ---" else None)
                if target_sym:
                    if target_sym[0].isdigit() and ".TW" not in target_sym: target_sym += ".TW"
                    mkt = "tw" if "台灣" in market_choice or ".TW" in target_sym else "us"
                    
                    display_name = target_sym
                    with st.spinner(f"🔍 正在獲取 {target_sym} 名稱資訊..."):
                        try:
                            if ".TW" in target_sym:
                                url = f"https://tw.stock.yahoo.com/quote/{target_sym}"
                                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                                res = requests.get(url, headers=headers, timeout=5)
                                soup = BeautifulSoup(res.text, 'html.parser')
                                title = soup.find('title').text
                                if " - " in title:
                                    # 🔥 V4.1.3 極端淨化法：直接用左括號切斷，例如 "2330 台積電(.TW) 走勢圖" -> "2330 台積電"
                                    clean_title = title.split(" - ")[0].split("(")[0]
                                    name_part = clean_title.replace(target_sym.replace('.TW', ''), '').strip()
                                    if name_part:
                                        display_name = name_part
                            else:
                                info = yf.Ticker(target_sym).info
                                fetched_name = info.get('shortName') or info.get('longName')
                                if fetched_name:
                                    display_name = fetched_name
                        except Exception as e:
                            pass
                    
                    db_manager.add_monitor_item(target_sym, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                    
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.execute("UPDATE monitor_pool SET display_name = ? WHERE ticker = ?", (display_name, target_sym))
                        
                    st.success(f"✅ 已將 {display_name} ({target_sym}) 加入實戰監測！")
                    st.rerun()
            
            st.markdown("<hr style='margin: 10px 0; border-color: #475569;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.9rem; font-weight:700; margin-bottom:5px;'>📥 回測填入</div>", unsafe_allow_html=True)
            
            if st.button("策略回測高分股票", use_container_width=True, key="btn_import_a"):
                st.toast("開發中：未來將自動讀取引擎算出的高分名單", icon="🚧")
                    
        with st.container(border=True):
            st.markdown("### 🗑️ 移除監測清單")
            del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=lambda x: monitor_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_a")
            if st.button("確認刪除", use_container_width=True, key="btn_del_a"):
                if del_sym != "--- 請選擇 ---":
                    db_manager.remove_monitor_item(del_sym)
                    st.success(f"🗑️ 已移除 {monitor_map.get(del_sym, del_sym)}")
                    st.rerun()

    # ==========================================
    # 🌟 頁面 B 專屬側邊欄 (Backtest)
    # ==========================================
    elif current_page == "🎯 頁面 B : 策略回測戰情":
        backtest_items = db_manager.get_all_backtest_items()
        backtest_tickers = [item['ticker'] for item in backtest_items]
        backtest_map = {item['ticker']: item['display_name'] for item in backtest_items}
        
        with st.container(border=True):
            st.markdown("### 🧪 回測策略設定")
            strategy = st.selectbox("選擇回測策略", ["趨勢動能策略 (Trend Momentum)", "均值回歸策略 (待開發)"])
            
        with st.container(border=True):
            st.markdown("### ➕ 新增回測母體 (免設警報)")
            market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_b")
            new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330", key="sym_manual_b").strip().upper()
            
            if st.button("確認新增至回測池", use_container_width=True, key="btn_add_b"):
                if new_sym:
                    if new_sym[0].isdigit() and ".TW" not in new_sym: new_sym += ".TW"
                    mkt = "tw" if "台灣" in market_choice or ".TW" in new_sym else "us"
                    db_manager.add_backtest_item(new_sym, market=mkt)
                    st.success(f"✅ 已將 {new_sym} 加入回測母體！")
                    st.rerun()
                    
            st.markdown("<hr style='margin: 10px 0; border-color: #475569;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.9rem; font-weight:700; margin-bottom:5px;'>🗂️ 族群批次輸入</div>", unsafe_allow_html=True)
            sector_options = ["--- 請選擇 ---"]
            sectors_data = {}
            sector_file = os.path.join(BASE_DIR, "config", "sectors.json")
            if os.path.exists(sector_file):
                with open(sector_file, "r", encoding="utf-8") as f:
                    try:
                        sectors_data = json.load(f)
                        sector_options.extend(list(sectors_data.keys()))
                    except Exception: pass
            
            selected_sector = st.selectbox("選擇族群", sector_options, key="sector_sel")
            if st.button("確認批次輸入", use_container_width=True, key="btn_sector_add"):
                if selected_sector != "--- 請選擇 ---":
                    tickers_to_add = sectors_data.get(selected_sector, [])
                    for t in tickers_to_add:
                        mkt = "tw" if ".TW" in t else "us"
                        db_manager.add_backtest_item(t, market=mkt)
                    st.success(f"✅ 已批次寫入 {len(tickers_to_add)} 檔標的！")
                    st.rerun()

        with st.container(border=True):
            st.markdown("### 🗑️ 移除回測清單")
            del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + backtest_tickers, format_func=lambda x: backtest_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_b")
            if st.button("確認刪除", use_container_width=True, key="btn_del_b"):
                if del_sym != "--- 請選擇 ---":
                    db_manager.remove_backtest_item(del_sym)
                    st.success(f"🗑️ 已移除 {backtest_map.get(del_sym, del_sym)}")
                    st.rerun()

        with st.container(border=True):
            st.markdown("### 📥 歷史資料庫管理")
            if st.button("強制更新 5 年歷史資料", use_container_width=True):
                if not backtest_tickers:
                    st.warning("⚠️ 回測池目前為空，請先新增股票！")
                else:
                    with st.spinner('🔄 正在向 Yahoo 請求 K 線資料...'):
                        success = data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True)
                        if success:
                            st.success("✅ 回測母體歷史資料更新完成！")
                            st.rerun()
                        else:
                            st.error("⚠️ 更新失敗，請檢查網路狀態。")

    # ==========================================
    # 🌟 共用底部區塊
    # ==========================================
    with st.container(border=True):
        st.markdown("### ⏱️ 網頁刷新頻率")
        refresh_sec = st.slider("秒", 5, 60, 30, label_visibility="collapsed")
        if st.button("🔄 手動立即刷新", use_container_width=True): st.rerun()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tpe_now = now_utc.astimezone(TAIPEI_TZ)
    tpe_time_str = tpe_now.strftime("%H:%M:%S %m/%d/%Y")
    
    st.markdown(
        f"""
        <div style="background-color:#1e293b; padding:12px; border-radius:8px; border:1px solid #475569; text-align:center; margin-top:15px; margin-bottom:15px;">
            <div style="color:#94a3b8; font-size:0.8rem; font-weight:600; margin-bottom:4px;">系統當前版本</div>
            <div style="color:#38bdf8; font-size:1.1rem; font-weight:700; margin-bottom:10px;">{APP_VERSION}</div>
            <div style="color:#94a3b8; font-size:0.8rem; font-weight:600; margin-bottom:8px;">🕒 系統當前時間</div>
            <div style="color:#f1f5f9; font-size:0.88rem; font-weight:600; margin-bottom:2px;">Tw {tpe_time_str}</div>
        </div>
        """, unsafe_allow_html=True
    )

# ==========================================================
# 5️⃣ 主畫面戰情室
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

if current_page == "📡 頁面 A : 即時雷達監測":
    ui_monitor.render_radar_dashboard()
            
elif current_page == "🎯 頁面 B : 策略回測戰情":
    ui_strategy.render_backtest_dashboard()
