# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 程式版本 : QBS_v2.1.1 (Phase 2: UI 視覺細節極致統一版)
# 📋 說明 : 統一系統導航外框、同步頁面 A/B 的次級標題與操作區排版。
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz
import os
import json
import sqlite3
from core import db_manager
from core import data_fetcher

# ==========================================================
# 1️⃣ 頁面設定與全域配置
# ==========================================================
st.set_page_config(page_title="QBS 量化回測系統", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(os.path.join("assets", "style.css"))

# ==========================================================
# 2️⃣ 系統全域常數與初始化
# ==========================================================
APP_VERSION = "QBS_v2.1.1"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: st.session_state.monitoring = False

test_display_map = {"2330.TW": "2330 台積電", "2454.TW": "2454 聯發科", "AAPL": "AAPL 蘋果", "NVDA": "NVDA 輝達"}

# ==========================================================
# 3️⃣ 側邊欄控制面板 (🔥 UI/UX 極致統一版)
# ==========================================================
with st.sidebar:
    # --- 系統導航 (已容器化) ---
    with st.container(border=True):
        st.markdown("### 🧭 系統導航")
        current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], label_visibility="collapsed", key="main_page_nav")
    
    # ==========================================
    # 🌟 頁面 A 專屬側邊欄 (Monitor)
    # ==========================================
    if current_page == "📡 頁面 A : 即時雷達監測":
        monitor_items = db_manager.get_all_monitor_items()
        monitor_tickers = [item['ticker'] for item in monitor_items]
        monitor_map = {item['ticker']: item['display_name'] for item in monitor_items}
        
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
            selected_db = st.selectbox("資料庫選取", ["--- 請選擇 ---", "2330.TW", "2454.TW", "AAPL", "NVDA"], format_func=lambda x: test_display_map.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_a")
            new_sym = st.text_input("或 手動輸入代碼", value="", key="sym_manual_a").strip().upper()
            th_text = st.text_input("提醒門檻 (%)", value="", key="th_a")
            entry_text = st.text_input("進場提醒 ($)", value="", key="entry_a")
            exit_text = st.text_input("出場提醒 ($)", value="", key="exit_a")
            
            if st.button("確認新增至監測池", use_container_width=True, key="btn_add_a"):
                target_sym = new_sym if new_sym else (selected_db if selected_db != "--- 請選擇 ---" else None)
                if target_sym:
                    if target_sym[0].isdigit() and ".TW" not in target_sym: target_sym += ".TW"
                    mkt = "tw" if ".TW" in target_sym else "us"
                    db_manager.add_monitor_item(target_sym, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                    st.rerun()
            
            # 🔥 V2.1.1 對齊頁面 B 風格
            st.markdown("<hr style='margin: 10px 0; border-color: #475569;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.9rem; font-weight:700; margin-bottom:5px;'>📥 回測填入</div>", unsafe_allow_html=True)
            if st.button("策略回測高分股票", use_container_width=True, key="btn_import_a"):
                st.toast("開發中：讀取高分名單...", icon="🚧")
                    
        with st.container(border=True):
            st.markdown("### 🗑️ 移除監測清單")
            del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=lambda x: monitor_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_a")
            if st.button("確認刪除", use_container_width=True, key="btn_del_a"):
                if del_sym != "--- 請選擇 ---":
                    db_manager.remove_monitor_item(del_sym); st.rerun()

    # ==========================================
    # 🌟 頁面 B 專屬側邊欄 (Backtest)
    # ==========================================
    elif current_page == "🎯 頁面 B : 策略回測戰情":
        backtest_items = db_manager.get_all_backtest_items()
        backtest_tickers = [item['ticker'] for item in backtest_items]
        backtest_map = {item['ticker']: item['display_name'] for item in backtest_items}
        
        with st.container(border=True):
            st.markdown("### 🧪 回測策略設定")
            strategy = st.selectbox("選擇回測策略", ["TW50 經典策略 (預設)"])
            
        with st.container(border=True):
            st.markdown("### ➕ 新增回測母體")
            new_sym = st.text_input("輸入股票代碼", value="", key="sym_manual_b").strip().upper()
            if st.button("確認新增至回測池", use_container_width=True, key="btn_add_b"):
                if new_sym:
                    if new_sym[0].isdigit() and ".TW" not in new_sym: new_sym += ".TW"
                    db_manager.add_backtest_item(new_sym, market="tw" if ".TW" in new_sym else "us"); st.rerun()
                    
            st.markdown("<hr style='margin: 10px 0; border-color: #475569;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.9rem; font-weight:700; margin-bottom:5px;'>🗂️ 族群批次輸入</div>", unsafe_allow_html=True)
            if st.button("確認批次輸入", use_container_width=True, key="btn_sector_add"): st.rerun()

        with st.container(border=True):
            st.markdown("### 🗑️ 移除回測清單")
            del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + backtest_tickers, format_func=lambda x: backtest_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_b")
            if st.button("確認刪除", use_container_width=True, key="btn_del_b"):
                if del_sym != "--- 請選擇 ---": db_manager.remove_backtest_item(del_sym); st.rerun()

        with st.container(border=True):
            st.markdown("### 📥 歷史資料庫管理")
            if st.button("強制更新 5 年歷史資料", use_container_width=True):
                with st.spinner('🔄 下載中...'):
                    data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True); st.rerun()

    # (底部資訊略...)
    st.markdown(f"<div style='text-align:center; padding:10px; color:#94a3b8; font-size:0.8rem;'>{APP_VERSION}</div>", unsafe_allow_html=True)

# ==========================================================
# 5️⃣ 主畫面 (純粹展示區)
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)
if current_page == "📡 頁面 A : 即時雷達監測":
    st.markdown("### 📡 實戰雷達監測 (Execution Battlefield)")
    st.info(f"💡 實戰彈藥庫目前共有 **{len(db_manager.get_all_monitor_items())}** 檔監測標的。")
elif current_page == "🎯 頁面 B : 策略回測戰情":
    st.markdown("### 🎯 策略回測戰情室 (The Research Hub)")
    count = 0
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn: count = conn.cursor().execute("SELECT COUNT(*) FROM daily_price").fetchone()[0]
    st.success(f"📊 **歷史資料庫實時狀態**：系統已儲存了 **{count:,}** 筆 K 線資料。")
