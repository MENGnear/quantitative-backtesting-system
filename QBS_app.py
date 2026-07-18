# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v1.4.0 (Phase 2: 側邊欄 UI 正式串接資料庫)
#
# 📋 進版說明 (Version Notes):
#   1. [串接] 匯入 core.db_manager，使前端 UI 能直接與 SQLite 互動。
#   2. [優化] 移除清單的下拉選單現在會動態讀取資料庫中的標的。
#   3. [功能] 實作「手動輸入股票」與「刪除標的」寫入/刪除資料庫並自動重新渲染 (rerun)。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置 (Page Config)
#   - 2️⃣ 動態載入外部深色視覺 CSS 樣板 (Load External CSS)
#   - 3️⃣ 系統全域常數與資料庫初始化 (State & DB Management) - 🔥 V1.4.0 更新
#   - 4️⃣ 側邊欄控制面板 (Sidebar Control Panel) - 🔥 V1.4.0 串接 CRUD
#   - 5️⃣ 主畫面分頁路由導覽 (Main Page Tab Navigation)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz
import os
from core import db_manager  # 🔥 匯入我們剛剛寫好的資料庫管理模組

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
    else:
        st.warning(f"⚠️ 找不到視覺樣板檔案: {file_path}")

load_css(os.path.join("assets", "style.css"))

# ==========================================================
# 3️⃣ 系統全域常數與資料庫/Session 初始化
# ==========================================================
APP_VERSION = "QBS_v1.4.0"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# 確保每次網頁啟動時，資料庫都有被正確初始化
if "db_initialized" not in st.session_state:
    db_manager.init_db()
    st.session_state.db_initialized = True

if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

# 每次渲染前，從資料庫撈出最新的監測清單
current_watchlist = db_manager.get_all_watchlist()
watchlist_tickers = [item['ticker'] for item in current_watchlist]

# ==========================================================
# 4️⃣ 側邊欄控制面板
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        st.markdown("### ⚙️ 控制與設定面板")
    
    # 1. 執行股票監測
    with st.container(border=True):
        st.markdown("### ▶️ 執行股票監測")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("開始", use_container_width=True): 
                st.session_state.monitoring = True
        with col_btn2:
            if st.button("暫停", use_container_width=True): 
                st.session_state.monitoring = False
                
        if st.session_state.monitoring: st.success("🟢 系統即時監測中...")
        else: st.info("🟡 監測暫停中")
    
    # 2. 新增監測股票
    with st.container(border=True):
        st.markdown("### ➕ 新增監測股票")
        
        # --- 區塊 0: 批次載入 TW50 ---
        if st.button("📥 一鍵載入 TW50 清單", use_container_width=True):
            st.toast("功能建置中... 將在後續實作批次寫入", icon="⏳")
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        
        # --- 區塊 A: 從市場資料庫選取 (暫保持 UI 測試) ---
        st.markdown("<div style='color:#facc15; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>📂 從市場資料庫選取</div>", unsafe_allow_html=True)
        market_choice = st.radio("選擇市場分類", ["tw 台灣", "us 美國"], horizontal=True, label_visibility="collapsed")
        
        if "台灣" in market_choice:
            selected_db = st.selectbox("tw 資料庫選取", ["--- 請選擇 ---", "2330.TW", "2454.TW"])
        else:
            selected_db = st.selectbox("us 資料庫選取", ["--- 請選擇 ---", "AAPL", "NVDA"])
            
        th_text_db = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_db")
        entry_text_db = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200", key="entry_db")
        exit_text_db = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190", key="exit_db")
        
        if st.button("確認輸入", use_container_width=True, key="btn_db"): 
            if selected_db != "--- 請選擇 ---":
                mkt = "tw" if "台灣" in market_choice else "us"
                db_manager.add_watchlist_item(selected_db, selected_db, mkt, th_text_db, entry_text_db, exit_text_db)
                st.success(f"✅ 已將 {selected_db} 加入資料庫！")
                st.rerun()
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        
        # --- 區塊 B: 手動輸入股票 ---
        st.markdown("<div style='color:#38bdf8; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>✍️ 手動輸入股票</div>", unsafe_allow_html=True)
        new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330.TW", key="sym_manual").strip().upper()
        th_text_manual = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_manual_2")
        entry_text_manual = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200", key="entry_manual_2")
        exit_text_manual = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190", key="exit_manual_2")
        
        if st.button("確認輸入 ", use_container_width=True, key="btn_manual_add"): 
            if new_sym:
                mkt = "tw" if ".TW" in new_sym else "us"
                db_manager.add_watchlist_item(new_sym, new_sym, mkt, th_text_manual, entry_text_manual, exit_text_manual)
                st.success(f"✅ 已將 {new_sym} 加入資料庫！")
                st.rerun()
            else:
                st.error("代碼不可為空！")
            
    # 3. 移除監測清單 (🔥 動態讀取資料庫)
    with st.container(border=True):
        st.markdown("### 🗑️ 移除監測清單")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + watchlist_tickers)
        if st.button("確認刪除", use_container_width=True):
            if del_sym != "--- 請選擇 ---":
                db_manager.remove_watchlist_item(del_sym)
                st.success(f"🗑️ 已從資料庫移除 {del_sym}")
                st.rerun()
            
    # 4. 網頁刷新頻率
    with st.container(border=True):
        st.markdown("### ⏱️ 網頁刷新頻率")
        refresh_sec = st.slider("秒", 5, 60, 30, label_visibility="collapsed")
        if st.button("🔄 手動立即刷新", use_container_width=True):
            st.rerun()

    # 5. 手動推播測試 & 強制更新
    with st.container(border=True):
        st.markdown("### 🛠️ 系統功能測試")
        if st.button("🚀 發送目前小卡狀態 (推播)", use_container_width=True):
            st.toast("UI 測試：推播指令已觸發", icon="✅")
        if st.button("📥 強制更新 5 年歷史資料", use_container_width=True):
            st.toast("UI 測試：資料庫更新指令已觸發", icon="✅")

    # 6. 系統當前版本
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
# 5️⃣ 主畫面分頁路由導覽
# ==========================================================
st.markdown('<h1 class="main-title">📈 Quantitative Backtesting System (QBS)</h1>', unsafe_allow_html=True)

# 利用 radio 建立分頁導覽
current_page = st.radio("main_nav", ["📡 頁面 A : 即時雷達監測", "🎯 頁面 B : 策略回測戰情"], horizontal=True, label_visibility="collapsed", key="main_page_nav")

# ----------------------------------------------------------
# 路由邏輯
# ----------------------------------------------------------
if current_page == "📡 頁面 A : 即時雷達監測":
    st.markdown("### 📡 即時雷達監測 (Monitor)")
    st.info(f"💡 目前資料庫共有 {len(watchlist_tickers)} 檔監測標的：{', '.join(watchlist_tickers)}")

elif current_page == "🎯 頁面 B : 策略回測戰情":
    st.markdown("### 🎯 策略回測戰情 (TW50)")
    st.info("💡 這裡未來將載入 `ui_strategy.py`。會直接讀取 SQLite 資料庫，極速渲染經雙重排序後的 TW50 策略小卡矩陣。")
