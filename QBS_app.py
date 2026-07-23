# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v4.6.0 (Phase 5: 強制清除快取與側邊欄去重)
#
# 📋 進版說明 (Version Notes):
#   1. [快取清創] 在新增與刪除動作成功後，強制執行 st.cache_data.clear()，徹底根除資料讀取中卡死問題。
#   2. [顯示優化] 側邊欄下拉選單加入智慧去重，拒絕冗長重複字串。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置
#   - 2️⃣ 動態載入外部深色視覺 CSS 樣板
#   - 3️⃣ 系統全域常數與資料庫初始化
#   - 4️⃣ 側邊欄控制面板 (🔥 V4.6.0 強制清除與去重)
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

APP_VERSION = "QBS_V3.1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

def sidebar_header(icon, title):
    st.markdown(f"""
        <div style="margin-top: 15px; margin-bottom: 12px;">
            <span style="font-size: 1.05rem; font-weight: 700; color: #60a5fa; letter-spacing: 1px;">{icon} {title}</span>
            <hr style="margin: 5px 0 0 0; border: 0; border-top: 1px dashed #475569;">
        </div>
    """, unsafe_allow_html=True)

test_display_map = {"2330.TW": "2330 台積電", "2454.TW": "2454 聯發科", "AAPL": "AAPL", "NVDA": "NVDA"}

# ==========================================================
# 4️⃣ 側邊欄控制面板
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
        
        # 🔥 側邊欄下拉選單智慧去重
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
                        db_manager.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                        
                        # 🔥 關鍵修復：新增成功後強制炸掉舊快取，保證小卡秒出
                        st.cache_data.clear()
                        
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
                    
                    # 🔥 關鍵修復：刪除成功後強制炸掉舊快取
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
            new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330", key="sym_manual_b").strip().upper()
            
            if st.button("確認新增", use_container_width=True, key="btn_add_b"):
                if new_sym:
                    if new_sym[0].isdigit() and ".TW" not in new_sym: new_sym += ".TW"
                    mkt = "tw" if "台灣" in market_choice or ".TW" in new_sym else "us"
                    db_manager.add_backtest_item(new_sym, market=mkt)
                    st.success(f"✅ {new_sym} 加入回測池！")
                    st.rerun()
                    
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
    # 🌟 版本控制塊 (絕對置中與去縮排)
    # ==========================================
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tpe_now = now_utc.astimezone(pytz.timezone('Asia/Taipei'))
    us_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    version_html = textwrap.dedent(f"""
    <div style="background-color:#0f172a; padding:12px; border-radius:8px; border:1px solid #1e293b; margin-top:10px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
        <div style="font-size: 0.9rem; font-weight: 700; color: #60a5fa; margin-bottom: 5px;">🗂️ 系統當前版本</div>
        <div style="color:#f8fafc; font-size:1rem; font-weight:700; margin-bottom:12px;">{APP_VERSION}</div>
        <div style="font-size: 0.9rem; font-weight: 700; color: #60a5fa; margin-bottom: 5px;">🕒 最後資料更新</div>
        <div style="color:#f1f5f9; font-size:0.85rem; font-weight:600; margin-bottom:4px;">Tw {tpe_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
        <div style="color:#f1f5f9; font-size:0.85rem; font-weight:600;">Us {us_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
    </div>
    """).strip()
    
    st.markdown(version_html, unsafe_allow_html=True)

# ==========================================================
# 5️⃣ 主畫面戰情室
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

if current_page == "📡 頁面 A : 即時雷達監測":
    ui_monitor.render_radar_dashboard()
elif current_page == "🎯 頁面 B : 策略回測戰情":
    ui_strategy.render_backtest_dashboard()
