# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.0.0 (Phase 4: 即時雷達視覺化看板)
#
# 📋 進版說明 (Version Notes):
#   1. [視覺] 建立雷達儀表板，將 monitor_pool 的監控數據具象化。
#   2. [報價] 呼叫 engine_monitor 獲取極速報價，動態顯示漲跌幅與顏色。
#   3. [警報] 獨立出「🚨 最新觸發警報」區塊，於上方醒目提示。
# ==========================================================

import streamlit as st
import pandas as pd
from core import engine_monitor

def render_radar_dashboard():
    """負責頁面 A 的整體即時雷達戰情室渲染"""
    st.markdown("### 📡 實戰雷達監測 (Execution Battlefield)")
    
    # 1. 取得監測名單
    targets_df = engine_monitor.get_monitor_targets()
    if targets_df.empty:
        st.info("💡 實戰彈藥庫目前為空，請先從左側「新增實戰監控」寫入標的。")
        return

    tickers = targets_df['ticker'].tolist()
    
    # 2. 獲取即時報價與執行雷達掃描 (觸發防連發冷卻機制)
    with st.spinner("📡 正在擷取即時報價與掃描防線..."):
        quotes = engine_monitor.fetch_realtime_quotes(tickers)
        alerts = engine_monitor.run_radar_scan()

    # 3. 🚨 最新警報區塊 (有警報才顯示)
    if alerts:
        st.markdown("#### 🚨 最新觸發警報")
        for alert in alerts:
            if '波動' in alert['type']:
                st.warning(f"**{alert['type']}** | {alert['name']}({alert['ticker']}): {alert['message']}")
            elif '進場' in alert['type']:
                st.success(f"**{alert['type']}** | {alert['name']}({alert['ticker']}): {alert['message']}")
            elif '出場' in alert['type']:
                st.error(f"**{alert['type']}** | {alert['name']}({alert['ticker']}): {alert['message']}")
        
        st.markdown("<hr style='margin: 15px 0; border-color: #334155;'>", unsafe_allow_html=True)

    # 4. 📊 監測標的即時狀態網格
    st.markdown("#### 📊 雷達掃描盤 (即時狀態)")
    
    cols_per_row = 3
    for i in range(0, len(targets_df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(targets_df):
                row = targets_df.iloc[i + j]
                ticker = row['ticker']
                name = row['display_name']
                
                with cols[j]:
                    with st.container(border=True):
                        # 標題
                        st.markdown(f"<div style='font-size: 1.1rem; font-weight: 700; color: #38bdf8;'>{ticker} <span style='font-size: 0.9rem; color: #94a3b8;'>{name}</span></div>", unsafe_allow_html=True)
                        
                        # 報價與漲跌幅判定
                        if ticker in quotes:
                            q = quotes[ticker]
                            curr = q['current']
                            chg = q['change_pct']
                            
                            color = "#ef4444" if chg < 0 else "#10b981"
                            sign = "+" if chg > 0 else ""
                            
                            st.markdown(f"<div style='color: {color}; font-size: 2rem; font-weight: 800; line-height: 1.2; margin-top: 5px;'>${curr} <span style='font-size: 1.2rem; font-weight: 600;'>({sign}{chg}%)</span></div>", unsafe_allow_html=True)
                            
                            # 顯示設定門檻
                            entry = row['entry_prices'] if pd.notna(row['entry_prices']) and row['entry_prices'] else "-"
                            exit_p = row['exit_prices'] if pd.notna(row['exit_prices']) and row['exit_prices'] else "-"
                            th = row['thresholds'] if pd.notna(row['thresholds']) and row['thresholds'] else "-"
                            
                            st.markdown(f"""
                            <div style="font-size:0.85rem; color:#94a3b8; margin-top:12px; border-top: 1px solid #334155; padding-top: 8px;">
                                <div style="display: flex; justify-content: space-between;"><span>🎯 進場設定:</span> <span style="color:#e2e8f0; font-weight: 600;">{entry}</span></div>
                                <div style="display: flex; justify-content: space-between;"><span>💰 出場設定:</span> <span style="color:#e2e8f0; font-weight: 600;">{exit_p}</span></div>
                                <div style="display: flex; justify-content: space-between;"><span>⚡ 波動門檻:</span> <span style="color:#e2e8f0; font-weight: 600;">{th}%</span></div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("<div style='color: #64748b; font-size: 1.2rem; margin-top: 15px;'>報價讀取中...</div>", unsafe_allow_html=True)
