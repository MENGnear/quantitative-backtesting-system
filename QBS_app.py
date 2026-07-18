# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : QBS_app.py
# 程式版本 : QBS_v1.0.0 (Phase 1: 骨架建置與視覺定錨)
#
# 📋 進版說明 (Version Notes):
#   1. [全新] 建立 QBS 專案入口網頁，融合 Monitor 與 TW50 雙系統介面。
#   2. [視覺] 完美繼承並鎖定原專案頂級深色優化視覺 CSS 樣板，確保 UI 體驗一致。
#   3. [導覽] 導入程式 C 的分頁導覽 (Tabs) 路由邏輯，實現單頁動態切換。
#   4. [擴充] 側邊欄 UI 新增「一鍵載入 TW50」與「手動更新 5 年歷史資料」按鈕骨架。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 頁面設定與全域配置 (Page Config)
#   - 2️⃣ 頂級深色優化視覺 CSS 樣板 (UI Lock-in)
#   - 3️⃣ 系統全域常數與 Session 狀態初始化 (State Management)
#   - 4️⃣ 側邊欄控制面板 (Sidebar Control Panel)
#   - 5️⃣ 主畫面分頁路由導覽 (Main Page Tab Navigation)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import datetime
import pytz

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
# 2️⃣ 頂級深色優化視覺 CSS 樣板 (嚴格保留原設定，不更動任何 Class)
# ==========================================================
st.markdown(r'''
<style>
/* =========================================
   1. 全域與基礎設定 (字體與網頁背景)
   ========================================= */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [data-testid="stAppViewContainer"] { 
    font-family: 'Inter', sans-serif !important; 
    background-color: #0e1117 !important; 
    color: #f1f5f9 !important; 
}
[data-testid="stActionElements"] { display: none !important; }
header[data-testid="stHeader"] { background-color: transparent !important; }
.main .block-container { padding-top: 1.5rem !important; margin-top: -30px !important; }
h1 { margin-top: 0px !important; padding-top: 0px !important; margin-bottom: 5px !important; }

/* =========================================
   2. 側邊欄與元件視覺 (輸入框、選單、按鈕)
   ========================================= */
[data-testid="stSidebar"] { 
    background-color: #171a23 !important; 
    border-right: 1px solid #2d3748 !important; 
}
[data-testid="stVerticalBlockBorderWrapper"] { 
    background-color: #1e293b !important; 
    border: 1px solid #94a3b8 !important; 
    border-radius: 12px !important; 
    padding: 15px !important; 
    margin-bottom: 10px !important; 
}
[data-testid="collapsedControl"] svg, [data-testid="stSidebarCollapseButton"] svg, button[kind="header"] svg { 
    color: #ffffff !important; fill: #ffffff !important; 
}
.stTextInput div[data-baseweb="input"], .stSelectbox div[data-baseweb="select"] > div { 
    background-color: #0f172a !important; 
    border: 1px solid #475569 !important; 
    border-radius: 8px !important;  
}
.stTextInput input { color: #ffffff !important; background-color: transparent !important; }
.stSelectbox div[data-baseweb="select"] span { color: #ffffff !important; }
[data-testid="stSidebar"] h3 { color: #ffffff !important; font-size: 1.1rem !important; font-weight: 700 !important; margin-bottom: 15px !important; margin-top: 0px !important; padding-top: 0px !important; }
[data-testid="stWidgetLabel"] p, div[data-testid="stMarkdownContainer"] p, .stSlider label { color: #cbd5e1 !important; font-weight: 600 !important; font-size: 0.95rem !important; }
div[role="radiogroup"] label { color: #f1f5f9 !important; font-weight: 600 !important; }

.stButton > button { 
    background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important; 
    color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; transition: all 0.2s ease !important; 
}
.stButton > button:hover { box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important; transform: translateY(-1px) !important; }

/* =========================================
   3. 矩陣排版與個股卡片基礎外觀
   ========================================= */
.section-title { font-size: 1.3rem; font-weight: 700; color: #f8fafc; margin: 15px 0 10px 0; padding-left: 8px; border-left: 4px solid #3b82f6; }
.flex-matrix-container { display: flex; flex-wrap: wrap; gap: 14px; width: 100%; justify-content: flex-start !important; margin-bottom: 15px; }
.stock-compact-card { 
    background-color: #171a23; 
    border: 1px solid #2d3748; 
    border-radius: 12px; padding: 16px; 
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); 
    width: 295px !important; max-width: 295px !important; min-width: 295px !important; box-sizing: border-box; 
}

.alert-tw-up { color: #ef4444; background-color: rgba(239, 68, 68, 0.2) !important; width: 100%; text-align: center; padding: 5px; border-radius: 6px; }

.card-title-txt { margin: 0 0 2px 0; font-size: 1.25rem; font-weight: 700; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; justify-content: space-between; align-items: baseline; }
.card-price-txt { color: #38bdf8; margin: 0 0 10px 0; font-size: 1.9rem; font-weight: 700; }
.card-middle-layout { display: flex; justify-content: space-between; margin-bottom: 4px; }
.layout-left-col { flex: 1.1; border-right: 1px dashed #2d3748; padding-right: 4px; text-align: left !important; line-height: 1.7; }
.layout-right-col { flex: 0.9; text-align: left !important; padding-left: 12px; line-height: 1.7; }
.txt-label { color: #94a3b8; font-size: 0.82rem; white-space: nowrap; } 
.txt-label-rsi { color: #a78bfa; font-size: 0.82rem; white-space: nowrap; } 
.txt-bold-val { color: #f1f5f9; font-size: 0.82rem; font-weight: 600; }
.custom-alert-box { min-height: 38px; display: flex; align-items: center; justify-content: center; border-radius: 6px; margin-top: 10px; font-size: 0.82rem; font-weight: 700; box-sizing: border-box; }

/* =========================================
   TW50 專屬卡片細節
   ========================================= */
h1.main-title { color: #f8fafc; font-weight: 800; text-align: left; padding-bottom: 10px; border-bottom: 2px solid #1e293b; margin-bottom: 20px; font-size: 1.8rem; }
.score-highlight { color: #facc15; font-size: 1.6rem; font-weight: 900; }

/* =========================================
   分頁選項專屬樣式 (從程式 C 繼承)
   ========================================= */
div[data-testid="stRadio"] div[role="radiogroup"] { gap: 10px; }
</style>
''', unsafe_allow_html=True)

# ==========================================================
# 3️⃣ 系統全域常數與 Session 狀態初始化
# ==========================================================
APP_VERSION = "QBS_v1.0.0"
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# 初始化 UI 狀態記憶 (Phase 1 骨架暫存)
if "monitoring" not in st.session_state: 
    st.session_state.monitoring = False

# ==========================================================
# 4️⃣ 側邊欄控制面板 (依據 A 面向與新需求 D1, D2 構建 UI)
# ==========================================================
with st.sidebar:
    with st.container(border=True):
        st.markdown("### ⚙️ 控制與設定面板")
    
    # 1. 執行股票監測 (原 Monitor 功能)
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
    
    # 2. 新增監測股票 (整合手動與 TW50 一鍵匯入)
    with st.container(border=True):
        st.markdown("### ➕ 新增監測股票")
        if st.button("📥 一鍵載入 TW50 清單", use_container_width=True):
            st.toast("UI 測試：TW50 載入指令已觸發", icon="✅")
            
        st.markdown("<hr style='margin: 15px 0; border-color: #475569;'>", unsafe_allow_html=True)
        st.markdown("<div style='color:#38bdf8; font-size:1.0rem; font-weight:700; margin-bottom:5px;'>✍️ 手動輸入股票</div>", unsafe_allow_html=True)
        new_sym = st.text_input("輸入股票代碼", value="", placeholder="例: AAPL 或 2330", key="sym_manual")
        th_text_manual = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_manual")
        entry_text_manual = st.text_input("進場提醒 ($)", value="", placeholder="例: 150, 200", key="entry_manual")
        exit_text_manual = st.text_input("出場提醒 ($)", value="", placeholder="例: 140, 190", key="exit_manual")
        
        if st.button("確認新增", use_container_width=True, key="btn_manual_add"): 
            st.toast(f"UI 測試：欲新增 {new_sym}", icon="✅")
            
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

    # 5. 手動推播測試 & 新需求 D2 (手動更新歷史資料)
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
# 5️⃣ 主畫面分頁路由導覽 (依據程式 C 架構萃取)
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
    # 未來實作：
    # import ui_monitor
    # ui_monitor.render_page()

elif current_page == "🎯 頁面 B : 策略回測戰情":
    st.markdown("### 🎯 策略回測戰情 (TW50)")
    st.info("💡 這裡未來將載入 `ui_strategy.py`。會直接讀取 SQLite 資料庫，極速渲染經雙重排序後的 TW50 策略小卡矩陣。")
    # 未來實作：
    # import ui_strategy
    # ui_strategy.render_page()
