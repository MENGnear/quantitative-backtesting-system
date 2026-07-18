# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v1.3.0 (Phase 1: 關注點分離，CSS 獨立模組化)
#
# 📋 進版說明 (Version Notes):
#   1. [重構] 依據【討論16】，將近百行的 CSS 程式碼從本檔抽離至 assets/style.css，落實前端關注點分離 (SoC)。
#   2. [優化] 區塊 2 加入動態讀取外部 CSS 檔案的 Python 邏輯，大幅精簡主程式長度。
#   3. [維持] 側邊欄 UI 與分頁路由等核心邏輯完全凍結不變，確保介面運作穩定。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置 (Page Config)
#   - 2️⃣ 動態載入外部深色視覺 CSS 樣板 (Load External CSS) - 🔥 V1.3.0 大幅更新
#   - 3️⃣ 系統全域常數與 Session 狀態初始化 (State Management)
#   - 4️⃣ 側邊欄控制面板 (Sidebar Control Panel)
#   - 5️⃣ 主畫面分頁路由導覽 (Main Page Tab Navigation)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz
import os

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
# 3️⃣ 系統全域常數與 Session 狀態初始化
# ==========================================================
APP_VERSION = "QBS_v1.3.0"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# 初始化 UI 狀態記憶 (Phase 1 骨架暫存)
if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

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
            st.toast("UI 測試：TW50 載入指令已觸發", icon="✅")
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        
        # --- 區塊 A: 從市場資料庫選取 ---
        st.markdown("<div style='color:#facc15; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>📂 從市場資料庫選取</div>", unsafe_allow_html=True)
        market_choice = st.radio("選擇市場分類", ["tw 台灣", "us 美國"], horizontal=True, label_visibility="collapsed")
        
        if "台灣" in market_choice:
            selected_db = st.selectbox("tw 資料庫選取", ["--- 請選擇 ---", "2330 台積電 (測試)"])
        else:
            selected_db = st.selectbox("us 資料庫選取", ["--- 請選擇 ---", "AAPL 蘋果 (測試)"])
            
        th_text_db = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_db")
        entry_text_db = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200 (當現價 >= 此設定觸發)", key="entry_db")
        exit_text_db = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190 (當現價 <= 此設定觸發)", key="exit_db")
        
        if st.button("確認輸入", use_container_width=True, key="btn_db"): 
            st.toast(f"UI 測試：從資料庫選取新增 {selected_db}", icon="✅")
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        
        # --- 區塊 B: 手動輸入股票 ---
        st.markdown("<div style='color:#38bdf8; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>✍️ 手動輸入股票</div>", unsafe_allow_html=True)
        new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330", key="sym_manual")
        th_text_manual = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_manual_2")
        entry_text_manual = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200 (當現價 >= 此設定觸發)", key="entry_manual_2")
        exit_text_manual = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190 (當現價 <= 此設定觸發)", key="exit_manual_2")
        
        if st.button("確認輸入 ", use_container_width=True, key="btn_manual_add"): 
            st.toast(f"UI 測試：手動新增 {new_sym}", icon="✅")
            
    # 3. 移除監測清單
    with st.container(border=True):
        st.markdown("### 🗑️ 移除監測清單")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---", "預設選項A", "預設選項B"])
        if st.button("確認刪除", use_container_width=True):
            st.toast("UI 測試：刪除指令已觸發", icon="✅")
            
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
# 路由邏輯：依據選擇的分頁，渲染對應的內容
# ----------------------------------------------------------
if current_page == "📡 頁面 A : 即時雷達監測":
    st.markdown("### 📡 即時雷達監測 (Monitor)")
    st.info("💡 這裡未來將載入 `ui_monitor.py`。會顯示大盤狀態，以及依據台美股時間自動切換的即時監測紅綠小卡。")

elif current_page == "🎯 頁面 B : 策略回測戰情":
    st.markdown("### 🎯 策略回測戰情 (TW50)")
    st.info("💡 這裡未來將載入 `ui_strategy.py`。會直接讀取 SQLite 資料庫，極速渲染經雙重排序後的 TW50 策略小卡矩陣。")
