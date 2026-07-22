# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v4.2.0 (Phase 5: MON 側邊欄美學與防呆機制)
#
# 📋 進版說明 (Version Notes):
#   1. [UI 重構] 全面淘汰 markdown 標題，使用專屬 HTML/CSS 打造精緻的 MON 層次感側邊欄。
#   2. [防呆機制] 恢復 MON 寫入前檢查機制：若查無名稱或代碼錯誤，直接阻擋寫入並提示錯誤，杜絕髒資料。
#   3. [精準爬蟲] 奇摩爬蟲與美股爬蟲極端淨化，美股僅保留代碼以維持版面整潔。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置
#   - 2️⃣ 動態載入外部深色視覺 CSS 樣板
#   - 3️⃣ 系統全域常數與資料庫初始化
#   - 4️⃣ 側邊欄控制面板 (🔥 V4.2.0 精緻美化與防呆守門員)
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

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css(os.path.join("assets", "style.css"))

APP_VERSION = "QBS_v4.2.0"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

# 用來產生美觀側邊欄標題的輔助函式
def sidebar_header(icon, title):
    st.markdown(f"""
        <div style="margin-top: 15px; margin-bottom: 12px;">
            <span style="font-size: 1.05rem; font-weight: 700; color: #60a5fa; letter-spacing: 1px;">{icon} {title}</span>
            <hr style="margin: 5px 0 0 0; border: 0; border-top: 1px dashed #475569;">
        </div>
    """, unsafe_allow_html=True)

test_display_map = {"2330.TW": "2330 台積電", "2454.TW": "2454 聯發科", "AAPL": "AAPL", "NVDA": "NVDA"}

# ==========================================================
# 4️⃣ 側邊欄控制面板 (🔥 精緻美化與防呆)
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        sidebar_header("🧭", "系統導航 (Navigation)")
        current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], label_visibility="collapsed", key="main_page_nav")
    
    if current_page == "📡 頁面 A : 即時雷達監測":
        monitor_items = db_manager.get_all_monitor_items()
        monitor_tickers = [item['ticker'] for item in monitor_items]
        monitor_map = {item['ticker']: f"{item['ticker']} {item['display_name']}" for item in monitor_items}
        
        with st.container(border=True):
            sidebar_header("▶️", "執行股票監測")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("開始", use_container_width=True, key="start_mon"): st.session_state.monitoring = True
            with col_btn2:
                if st.button("暫停", use_container_width=True, key="stop_mon"): st.session_state.monitoring = False
            if st.session_state.monitoring: st.success("🟢 即時監測中")
            else: st.info("🟡 監測暫停中")
            
        with st.container(border=True):
            sidebar_header("➕", "新增實戰監控 (需設警報)")
            market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_a")
            
            if "台灣" in market_choice:
                selected_db = st.selectbox("tw 資料庫選取", ["--- 請選擇 ---", "2330.TW", "2454.TW"], format_func=lambda x: test_display_map.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_tw_a")
            else:
                selected_db = st.selectbox("us 資料庫選取", ["--- 請選擇 ---", "AAPL", "NVDA"], format_func=lambda x: test_display_map.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_us_a")
                
            new_sym = st.text_input("或 手動輸入代碼", value="", placeholder="例: 6531", key="sym_manual_a").strip().upper()
            
            st.markdown("<div style='font-size:0.85rem; color:#94a3b8; margin-bottom:5px;'>監控條件設定：</div>", unsafe_allow_html=True)
            th_text = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_a", label_visibility="collapsed")
            entry_text = st.text_input("進場提醒 ($)", value="", placeholder="進場價 (例: 150)", key="entry_a", label_visibility="collapsed")
            exit_text = st.text_input("出場提醒 ($)", value="", placeholder="出場價 (例: 190)", key="exit_a", label_visibility="collapsed")
            
            if st.button("確認新增", use_container_width=True, key="btn_add_a"):
                target_sym = new_sym if new_sym else (selected_db if selected_db != "--- 請選擇 ---" else None)
                if target_sym:
                    if target_sym[0].isdigit() and ".TW" not in target_sym: target_sym += ".TW"
                    mkt = "tw" if "台灣" in market_choice or ".TW" in target_sym else "us"
                    
                    display_name = ""
                    is_valid = False
                    
                    with st.spinner(f"🔍 驗證標的與獲取名稱中..."):
                        try:
                            if ".TW" in target_sym:
                                url = f"https://tw.stock.yahoo.com/quote/{target_sym}"
                                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                                soup = BeautifulSoup(res.text, 'html.parser')
                                title = soup.find('title').text
                                if " - " in title:
                                    clean_title = title.split(" - ")[0].split("(")[0]
                                    name_part = clean_title.replace(target_sym.replace('.TW', ''), '').strip()
                                    if name_part:
                                        display_name = name_part
                                        is_valid = True
                            else:
                                # 美股驗證：確保有此股票，但顯示名稱只用代碼，保持版面乾淨
                                info = yf.Ticker(target_sym).fast_info
                                if 'lastPrice' in info or 'previousClose' in info:
                                    display_name = target_sym
                                    is_valid = True
                        except Exception:
                            is_valid = False
                    
                    # 🔥 MON 防呆守門員：無效代碼拒絕寫入
                    if is_valid:
                        db_manager.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                        st.success(f"✅ {display_name} ({target_sym}) 新增成功！")
                        st.rerun()
                    else:
                        st.error("❌ 查無此股票或獲取失敗，拒絕寫入！")
            
            st.markdown("<hr style='margin: 10px 0; border-color: #334155;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.85rem; font-weight:700; margin-bottom:5px;'>📥 回測結果匯入</div>", unsafe_allow_html=True)
            if st.button("載入策略高分股", use_container_width=True, key="btn_import_a"):
                st.toast("開發中：未來將自動讀取引擎算出的高分名單", icon="🚧")
                    
        with st.container(border=True):
            sidebar_header("🗑️", "移除監測標的")
            del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=lambda x: monitor_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_a", label_visibility="collapsed")
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
            sidebar_header("🧪", "回測策略設定")
            strategy = st.selectbox("選擇策略", ["趨勢動能策略 (Trend Momentum)", "均值回歸策略 (待開發)"], label_visibility="collapsed")
            
        with st.container(border=True):
            sidebar_header("➕", "新增回測母體 (純淨運算)")
            market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_b")
            new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330", key="sym_manual_b").strip().upper()
            
            if st.button("確認新增", use_container_width=True, key="btn_add_b"):
                if new_sym:
                    if new_sym[0].isdigit() and ".TW" not in new_sym: new_sym += ".TW"
                    mkt = "tw" if "台灣" in market_choice or ".TW" in new_sym else "us"
                    db_manager.add_backtest_item(new_sym, market=mkt)
                    st.success(f"✅ {new_sym} 加入回測池！")
                    st.rerun()
                    
            st.markdown("<hr style='margin: 10px 0; border-color: #334155;'>", unsafe_allow_html=True)
            st.markdown("<div style='color:#a78bfa; font-size:0.85rem; font-weight:700; margin-bottom:5px;'>🗂️ 族群批次輸入</div>", unsafe_allow_html=True)
            sector_options = ["--- 請選擇 ---"]
            sectors_data = {}
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
            sidebar_header("📥", "歷史資料庫管理")
            if st.button("強制更新 5 年歷史資料", use_container_width=True):
                if not backtest_tickers:
                    st.warning("⚠️ 回測池目前為空")
                else:
                    with st.spinner('🔄 請求 K 線資料...'):
                        success = data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True)
                        if success: st.success("✅ 更新完成！")
                        else: st.error("⚠️ 更新失敗")

    with st.container(border=True):
        sidebar_header("⏱️", "系統狀態")
        refresh_sec = st.slider("刷新頻率(秒)", 5, 60, 30)
        if st.button("🔄 手動刷新", use_container_width=True): st.rerun()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tpe_now = now_utc.astimezone(TAIPEI_TZ)
    st.markdown(f"""
        <div style="background-color:#0f172a; padding:12px; border-radius:8px; border:1px solid #1e293b; text-align:center; margin-top:10px;">
            <div style="color:#94a3b8; font-size:0.75rem; margin-bottom:2px;">Version {APP_VERSION}</div>
            <div style="color:#38bdf8; font-size:0.9rem; font-weight:700;">Tw {tpe_now.strftime("%H:%M:%S %m/%d")}</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================================
# 5️⃣ 主畫面戰情室
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

if current_page == "📡 頁面 A : 即時雷達監測":
    ui_monitor.render_radar_dashboard()
elif current_page == "🎯 頁面 B : 策略回測戰情":
    ui_strategy.render_backtest_dashboard()
