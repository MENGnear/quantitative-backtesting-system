# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v4.17.0 (Pre-Phase 7: 微前端路由重構)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 落實微前端 (Micro-Frontend) 設計模式，將側邊欄邏輯徹底解耦。
#   2. [職責分離] QBS_app.py 削瘦為純粹的「全域路由器 (Router)」，不再處理新增/刪除股票等業務邏輯。
#   3. [防呆傳遞] 將共用字典與格式化函式，透過依賴注入 (Dependency Injection) 傳遞給子模組。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置
#   - 2️⃣ 動態字典管理
#   - 3️⃣ 路由共用 UI 渲染函式
#   - 4️⃣ 中央路由分發台 (Router)
#   - 5️⃣ 主畫面戰情室與心跳引擎
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import datetime
import pytz
import os
import json
import textwrap
from core import db_manager
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

APP_VERSION = "QBS_V4.17.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")
DICT_PATH = os.path.join(BASE_DIR, "config", "stock_dict.json")

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css(os.path.join("assets", "style.css"))

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
tw_options = ["--- 請選擇 ---"] + sorted([k for k in stock_dict.keys() if k.endswith(".TW")])
us_options = ["--- 請選擇 ---"] + sorted([k for k in stock_dict.keys() if not k.endswith(".TW")])

# ==========================================================
# 3️⃣ 路由共用 UI 渲染函式
# ==========================================================
def sidebar_header(icon, title):
    header_html = textwrap.dedent(f"""
    <div style="margin-top: 0px; margin-bottom: 12px;">
        <span style="font-size: 1.05rem; font-weight: 700; color: #60a5fa; letter-spacing: 1px;">{icon} {title}</span>
        <hr style="margin: 5px 0 0 0; border: 0; border-top: 1px dashed #475569;">
    </div>
    """).strip()
    st.markdown(header_html, unsafe_allow_html=True)

def format_tw_option(x):
    if x == "--- 請選擇 ---": 
        return x
    code = x.replace(".TW", "")
    raw_name = stock_dict.get(x, x)
    if code in raw_name:
        return raw_name
    return f"{code} {raw_name}"

# ==========================================================
# 4️⃣ 中央路由分發台 (Router)
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        sidebar_header("🧭", "系統操作導航")
        current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], label_visibility="collapsed", key="main_page_nav")
    
    # 呼叫微前端專屬側邊欄 (Dependency Injection)
    if current_page == "📡 頁面 A : 即時雷達監測":
        if hasattr(ui_monitor, 'render_sidebar'):
            ui_monitor.render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header)
        else:
            st.warning("⚠️ 請更新 ui_monitor.py 實作 render_sidebar")
    elif current_page == "🎯 頁面 B : 策略回測戰情":
        if hasattr(ui_strategy, 'render_sidebar'):
            ui_strategy.render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header)
        else:
            st.warning("⚠️ 請更新 ui_strategy.py 實作 render_sidebar")

    # 手動測試推播元件
    if hasattr(ui_monitor, 'render_telegram_manual_test_ui'):
        ui_monitor.render_telegram_manual_test_ui()
            
    # 版本控制塊
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tpe_now = now_utc.astimezone(pytz.timezone('Asia/Taipei'))
    us_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    version_html = textwrap.dedent(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin-top: 15px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
        <div style="font-size: 0.9rem; font-weight: 600; color: #9ca3af; margin-bottom: 5px;">系統當前版本</div>
        <div style="color: #38bdf8; font-size: 1.15rem; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px;">{APP_VERSION}</div>
        <div style="font-size: 0.9rem; font-weight: 600; color: #9ca3af; margin-bottom: 5px;">🕒 最後資料更新</div>
        <div style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;">Tw {tpe_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
        <div style="color: #f1f5f9; font-size: 0.85rem; font-weight: 600;">Us {us_now.strftime("%H:%M:%S %m/%d/%Y")}</div>
    </div>
    """).strip()
    st.markdown(version_html, unsafe_allow_html=True)

# ==========================================================
# 5️⃣ 主畫面戰情室與心跳引擎
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

if current_page == "📡 頁面 A : 即時雷達監測":
    if hasattr(ui_monitor, 'render_radar_dashboard'):
        ui_monitor.render_radar_dashboard()
elif current_page == "🎯 頁面 B : 策略回測戰情":
    if hasattr(ui_strategy, 'render_backtest_dashboard'):
        ui_strategy.render_backtest_dashboard()

refresh_interval = st.session_state.get("refresh_a", 30) if current_page == "📡 頁面 A : 即時雷達監測" else st.session_state.get("refresh_b", 30)
st_autorefresh(interval=refresh_interval * 1000, key="qbs_heartbeat")
