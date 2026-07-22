# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.2.2 (Phase 4.1: MON 視覺比例精準還原版)
#
# 📋 進版說明 (Version Notes):
#   1. [版面優化] 調降 padding 釋放空間，加入 white-space: nowrap 防止文字換行，修正卡片被擠壓變窄的問題。
#   2. [字級對齊] 調降標題與價格字級，嚴格對齊 MON.png 原始設計的層次與美感。
#   3. [防護] 嚴守無縮排 HTML 輸出，避免 Streamlit Markdown 誤判。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 資料獲取與快取防護罩
#   - 2️⃣ 介面渲染主程式
#   - 3️⃣ 動態狀態機與無縮排 HTML 小卡生成 (🔥 V1.2.2 CSS 修正核心)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import pandas as pd
from core import engine_monitor

# ==========================================================
# 1️⃣ 資料獲取與快取防護罩
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_radar_data():
    return engine_monitor.run_radar_scan()

# ==========================================================
# 2️⃣ 介面渲染主程式
# ==========================================================
def render_radar_dashboard():
    st.markdown("### 📡 實戰雷達監測 (Execution Battlefield)")
    
    targets_df = engine_monitor.get_monitor_targets()
    if targets_df.empty:
        st.info("💡 實戰彈藥庫目前為空，請先從左側「新增實戰監控」寫入標的。")
        return

    with st.spinner("📡 正在擷取即時報價與掃描防線 (每 60 秒自動更新)..."):
        quotes, alerts = get_cached_radar_data()

    cols_per_row = 3
    for i in range(0, len(targets_df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(targets_df):
                row = targets_df.iloc[i + j]
                ticker = row['ticker']
                
                clean_ticker = ticker.replace('.TW', '')
                clean_name = row['display_name']

                with cols[j]:
                    if ticker in quotes:
                        q = quotes[ticker]
                        curr = q['current']
                        prev = q['prev']
                        open_p = q['open']
                        chg_amt = q['change_amt']
                        chg_pct = q['change_pct']
                        
                        # ==========================================================
                        # 3️⃣ 動態狀態機與無縮排 HTML 小卡生成 (🔥 V1.2.2 CSS 修正核心)
                        # ==========================================================
                        is_tw = ".TW" in ticker
                        
                        if chg_amt > 0:
                            bg_color = "#2a1518" if is_tw else "#15261e"
                            border_color = "#5a262c" if is_tw else "#1f4738"
                            text_color = "#ef4444" if is_tw else "#10b981"
                            sign = "+"
                        elif chg_amt < 0:
                            bg_color = "#15261e" if is_tw else "#2a1518"
                            border_color = "#1f4738" if is_tw else "#5a262c"
                            text_color = "#10b981" if is_tw else "#ef4444"
                            sign = ""
                        else:
                            bg_color = "#1c191b"
                            border_color = "#3d2a2e"
                            text_color = "#cbd5e1"
                            sign = ""
                            
                        chg_str = f"{sign}{chg_amt:.2f} ({sign}{chg_pct:.2f}%)"
                        
                        badge_html = ""
                        ticker_alerts = [a for a in alerts if a['ticker'] == ticker]
                        if ticker_alerts:
                            latest_alert = ticker_alerts[0]
                            badge_html = f"<div style='margin-top: 15px; background-color: {bg_color}; color: {text_color}; padding: 12px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 0.95rem; border: 1px solid {text_color}; box-shadow: inset 0 0 8px rgba(0,0,0,0.5);'>📈 觸發: {latest_alert['message']}</div>"

                        th_raw = row['thresholds'] if pd.notna(row['thresholds']) and row['thresholds'] else "--"
                        en_raw = row['entry_prices'] if pd.notna(row['entry_prices']) and row['entry_prices'] else "--"
                        ex_raw = row['exit_prices'] if pd.notna(row['exit_prices']) and row['exit_prices'] else "--"

                        # 🚨 V1.2.2 CSS 優化：縮小 Padding、設定標題 nowrap、縮小標題與價格字級
                        html = f"""<div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between; transition: all 0.3s ease;">
<div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{clean_ticker} {clean_name}</div>
<div style="font-size: 2.2rem; font-weight: 800; color: #38bdf8; margin-bottom: 16px;">${curr:.2f}</div>
<div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px;">
    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">昨收： <span style="color: #f8fafc; margin-left: 5px;">${prev:.2f}</span></div>
    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">開盤： <span style="color: #f8fafc; margin-left: 5px;">${open_p:.2f}</span></div>
    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">漲幅： <span style="color: {text_color}; margin-left: 5px;">{chg_str}</span></div>
</div>
<div style="border-top: 1px dashed #475569; padding-top: 12px; text-align: center; color: #64748b; font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">門檻: {th_raw}% | 進場: ${en_raw} | 出場: ${ex_raw}</div>
{badge_html}
</div>"""
                        st.markdown(html, unsafe_allow_html=True)
                    else:
                        html_loading = f"""<div style="background-color: #1c191b; border: 1px solid #3d2a2e; border-radius: 12px; padding: 18px 20px;">
<div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{clean_ticker} {clean_name}</div>
<div style="color: #64748b; font-size: 1.1rem; margin-top: 20px;">資料讀取中...</div>
</div>"""
                        st.markdown(html_loading, unsafe_allow_html=True)
