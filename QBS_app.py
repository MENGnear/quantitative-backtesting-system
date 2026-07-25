# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v4.11.0 (Phase 6: 版本區塊原生容器對齊版)
#
# 📋 進版說明 (Version Notes):
#   1. [底色修復] 捨棄 HTML 寫死的背景與邊框，改用 Streamlit 原生的 st.container(border=True) 進行包裝，完美還原 MON 的深色一體成型質感。
#   2. [連動修復] 拔除不必要的字串替換語法，讓畫面的 {APP_VERSION} 100% 忠實反應變數設定，恢復同步更新功能。
#   3. [功能保留] 完整繼承 V4.9.0 的動態字典記憶、頁面 A/B 同步連動、生命週期防護與快取動態清除。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置
#   - 2️⃣ 動態字典管理 
#   - 3️⃣ UX 連動回呼函式與信號燈初始化 
#   - 4️⃣ 系統全域常數與共用 UI 渲染 
#   - 5️⃣ 側邊欄控制面板 
#   - 6️⃣ 主畫面戰情室與原生版本區塊 (🔥 V4.11.0 原生容器與同步修復)
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
import textwrap
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

APP_VERSION = "QBS_V4.11.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")
DICT_PATH = os.path.join(BASE_DIR, "config", "stock_dict.json")

if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

# ==========================================================
# 2️⃣ 動態字典管理
# ==========================================================
def load_stock_dict():
    if not os.path.exists(os.path.dirname(DICT_PATH)):
        os.makedirs(os.path.dirname(DICT_PATH))
    if os.path.exists(DICT_PATH):
        try:
            with open(DICT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    default_dict = {"2330.TW": "2330 台積電", "2454.TW": "2454 聯發科", "AAPL": "AAPL", "NVDA": "NVDA"}
    save_stock_dict(default_dict)
    return default_dict

def save_stock_dict(data):
    with open(DICT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

stock_dict = load_stock_dict()

# ==========================================================
# 3️⃣ UX 連動回呼函式與信號燈初始化
# ==========================================================
if "sel_tw_val" not in st.session_state: st.session_state.sel_tw_val = "--- 請選擇 ---"
if "sel_us_val" not in st.session_state: st.session_state.sel_us_val = "--- 請選擇 ---"
if "manual_sym_val" not in st.session_state: st.session_state.manual_sym_val = ""
if "clear_input_flag" not in st.session_state: st.session_state.clear_input_flag = False

if "sel_tw_val_b" not in st.session_state: st.session_state.sel_tw_val_b = "--- 請選擇 ---"
if "sel_us_val_b" not in st.session_state: st.session_state.sel_us_val_b = "--- 請選擇 ---"
if "manual_sym_val_b" not in st.session_state: st.session_state.manual_sym_val_b = ""
if "clear_input_flag_b" not in st.session_state: st.session_state.clear_input_flag_b = False

def on_sel_change():
    st.session_state.manual_sym_val = ""
def on_manual_change():
    if st.session_state.manual_sym_val.strip() != "":
        st.session_state.sel_tw_val = "--- 請選擇 ---"
        st.session_state.sel_us_val = "--- 請選擇 ---"

def on_sel_change_b():
    st.session_state.manual_sym_val_b = ""
def on_manual_change_b():
    if st.session_state.manual_sym_val_b.strip() != "":
        st.session_state.sel_tw_val_b = "--- 請選擇 ---"
        st.session_state.sel_us_val_b = "--- 請選擇 ---"

# ==========================================================
# 4️⃣ 系統全域常數與共用 UI 渲染
# ==========================================================
def sidebar_header(icon, title):
    header_html = textwrap.dedent(f"""
    <div style="margin-top: 0px; margin-bottom: 12px;">
        <span style="font-size: 1.05rem; font-weight: 700; color: #60a5fa; letter-spacing: 1px;">{icon} {title}</span>
        <hr style="margin: 5px 0 0 0; border: 0; border-top: 1px dashed #475569;">
    </div>
    """).strip()
    st.markdown(header_html, unsafe_allow_html=True)

tw_options = ["--- 請選擇 ---"] + sorted([k for k in stock_dict.keys() if k.endswith(".TW")])
us_options = ["--- 請選擇 ---"] + sorted([k for k in stock_dict.keys() if not k.endswith(".TW")])

# ==========================================================
# 5️⃣ 側邊欄控制面板
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        sidebar_header("🧭", "系統操作導航")
        current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], label_visibility="collapsed", key="main_page_nav")
    
    # ==========================================
    # 🌟 頁面 A 專屬側邊欄
    # ==========================================
    if current_page == "📡 頁面 A : 即時雷達監測":
        monitor_items = db_manager.get_all_monitor_items()
        monitor_tickers = [item['ticker'] for item in monitor_items]
        
        monitor_map = {}
        for item in monitor_items:
            t = item['ticker']
            ct = t.replace('.TW', '')
            dn = str(item['display_name']).strip()
            if not dn or dn == t or dn == ct:
                monitor_map[t] = f"{ct}"
            elif dn.startswith(ct):
                monitor_map[t] = f"{dn}"
            else:
                monitor_map[t] = f"{ct} {dn}"
        
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
            sidebar_header("➕", "新增即時監控")
            market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_a")
            
            if "台灣" in market_choice:
                selected_db = st.selectbox("tw 資料庫選取", tw_options, format_func=lambda x: stock_dict.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_tw_val", on_change=on_sel_change)
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
                    st.warning("⚠️ 請至少輸入一項監控條件 (門檻%、進場價或出場價)！")
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
                                    url = f"https://tw.stock.yahoo.com/quote/{target_sym}"
                                    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                                    soup = BeautifulSoup(res.text, 'html.parser')
                                    title = soup.find('title').text
                                    if " - " in title:
                                        clean_title = title.split(" - ")[0].split("(")[0]
                                        name_part = clean_title.replace(target_sym.replace('.TW', ''), '').strip()
                                        if name_part:
                                            display_name = name_part
                                            is_valid = True
                                else:
                                    fi = yf.Ticker(target_sym).fast_info
                                    if fi.last_price is not None:
                                        display_name = target_sym
                                        is_valid = True
                            except Exception:
                                is_valid = False
                        
                        if is_valid:
                            if target_sym not in stock_dict or stock_dict[target_sym] != display_name:
                                stock_dict[target_sym] = display_name
                                save_stock_dict(stock_dict)

                            db_manager.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                            st.cache_data.clear()
                            st.session_state.clear_input_flag = True
                            st.success(f"✅ {display_name} ({target_sym}) 新增成功！")
                            st.rerun()
                        else:
                            st.error("❌ 查無此股票或獲取失敗，拒絕寫入！")
            
        with st.container(border=True):
            sidebar_header("📥", "回測結果匯入")
            if st.button("載入策略高分股", use_container_width=True, key="btn_import_a"):
                st.toast("開發中：未來將自動讀取引擎算出的高分名單", icon="🚧")
                    
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
            refresh_sec = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_a")
            if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_a"): 
                st.cache_data.clear()
                st.rerun()

    # ==========================================
    # 🌟 頁面 B 專屬側邊欄
    # ==========================================
    elif current_page == "🎯 頁面 B : 策略回測戰情":
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
                selected_db_b = st.selectbox("tw 資料庫選取", tw_options, format_func=lambda x: stock_dict.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_tw_val_b", on_change=on_sel_change_b)
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
                                url = f"https://tw.stock.yahoo.com/quote/{target_sym_b}"
                                res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
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
                else:
                    st.warning("⚠️ 請選擇或輸入標的代碼！")
                    
        with st.container(border=True):
            sidebar_header("🗂️", "族群批次輸入")
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
            sidebar_header("📥", "歷史資料管理")
            if st.button("強制更新 5 年歷史資料", use_container_width=True):
                if not backtest_tickers:
                    st.warning("⚠️ 回測池目前為空")
                else:
                    with st.spinner('🔄 請求 K 線資料...'):
                        success = data_fetcher.smart_update_historical_data(tickers=backtest_tickers, force_5y=True)
                        if success: st.success("✅ 更新完成！")
                        else: st.error("⚠️ 更新失敗")

        with st.container(border=True):
            sidebar_header("⏱️", "系統運行狀態")
            refresh_sec = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_b")
            if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_b"): st.rerun()

    # ==========================================
    # 🌟 版本控制塊 (🔥 V4.11.0 改用原生容器，還原同步連動)
    # ==========================================
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tpe_now = now_utc.astimezone(pytz.timezone('Asia/Taipei'))
    us_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    with st.container(border=True):
        version_html = textwrap.dedent(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 5px 0;">
            <div style="font-size: 0.85rem; font-weight: 600; color: #9ca3af; margin-bottom: 4px;">系統當前版本</div>
            <div style="color: #38bdf8; font-size: 1.1rem; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px;">{APP_VERSION}</div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #9ca3af; margin-bottom: 6px;">🕒 最後資料更新</div>
            <div style="color: #f1f5f9; font-size: 0.82rem; font-weight: 600; margin-bottom: 3px;">Tw {tpe_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
            <div style="color: #f1f5f9; font-size: 0.82rem; font-weight: 600;">Us {us_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
        </div>
        """).strip()
        st.markdown(version_html, unsafe_allow_html=True)

# ==========================================================
# 6️⃣ 主畫面戰情室
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

if current_page == "📡 頁面 A : 即時雷達監測":
    ui_monitor.render_radar_dashboard()
elif current_page == "🎯 頁面 B : 策略回測戰情":
    ui_strategy.render_backtest_dashboard()
