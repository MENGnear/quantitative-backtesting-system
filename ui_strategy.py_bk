# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_strategy.py
# 程式版本 : ui_v1.0.0 (Phase 3: 戰情室小卡渲染模組)
#
# 📋 進版說明 (Version Notes):
#   1. [新增] 實作動態網格佈局 (Grid Layout)，自動將 DataFrame 轉換為 4 欄並排的股票小卡。
#   2. [視覺] 導入分數門檻高光機制 (>= 45 分以綠色醒目標示，底背離掛上專屬 Tag)。
#   3. [串接] 完美對接 core.engine_core 的趨勢動能運算大腦。
# ==========================================================

import streamlit as st
import pandas as pd
from core import engine_core

def render_stock_card(row):
    """渲染單張股票戰情小卡 (HTML/CSS)"""
    # 分數顏色判定 (大於等於 45 分為強勢綠色，30-44 為黃色，低於 30 為紅色)
    total_score = row['總分']
    if total_score >= 45:
        score_color = "#10b981" # 翡翠綠
    elif total_score >= 30:
        score_color = "#fbbf24" # 琥珀黃
    else:
        score_color = "#ef4444" # 玫瑰紅
        
    # 背離標籤判定
    divergence_tag = ""
    if row['底背離'] == '✅':
        divergence_tag = "<span style='background-color:#7c3aed; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold; margin-left:8px;'>🚨 底背離</span>"

    # 小卡 HTML 結構
    card_html = f"""
    <div style="padding: 10px; display: flex; flex-direction: column; gap: 8px;">
        <!-- 頂部：代碼與名稱 -->
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 1.1rem; font-weight: 700; color: #38bdf8;">
                {row['代碼']} <span style="font-size: 0.9rem; color: #94a3b8;">{row['名稱']}</span>
            </div>
            {divergence_tag}
        </div>
        
        <!-- 中間：總分 (視覺焦點) -->
        <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #334155; padding-bottom: 8px;">
            <div style="font-size: 0.85rem; color: #94a3b8; font-weight: 600;">策略總分</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: {score_color}; line-height: 1;">
                {int(total_score)}<span style="font-size: 1rem; color: #64748b; font-weight: 600;">/80</span>
            </div>
        </div>
        
        <!-- 底部：細節數據 -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; row-gap: 6px; font-size: 0.85rem;">
            <div style="color: #cbd5e1;">收盤價：<span style="color: #f8fafc; font-weight: 600;">${row['收盤價']:.2f}</span></div>
            <div style="color: #cbd5e1;">RSI_14：<span style="color: #f8fafc; font-weight: 600;">{row['RSI_14']:.1f}</span></div>
            <div style="color: #94a3b8; font-size: 0.8rem;">趨勢(60)：<span style="color: #cbd5e1;">{int(row['趨勢分(60)'])}</span></div>
            <div style="color: #94a3b8; font-size: 0.8rem;">紅利(20)：<span style="color: #cbd5e1;">{int(row['紅利分(20)'])}</span></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def render_backtest_dashboard():
    """負責頁面 B 的整體回測戰情室渲染"""
    st.markdown("### 🎯 策略回測戰情室 (The Research Hub)")
    
    with st.spinner("🧠 核心引擎運算中，正在掃描技術指標與背離訊號..."):
        # 呼叫核心大腦取得算好的 DataFrame
        result_df = engine_core.run_trend_momentum_analysis()
        
    if result_df.empty:
        st.warning("⚠️ 尚無回測結果，請確認左側「回測母體」是否有新增股票，並已下載歷史資料。")
        return
        
    # 計算及格檔數
    pass_count = len(result_df[result_df['總分'] >= 45])
    st.info(f"💡 運算完成！共分析 **{len(result_df)}** 檔標的，其中有 **{pass_count}** 檔突破 45 分強勢門檻。")
    
    # 建立動態網格 (每排 4 欄)
    cols_per_row = 4
    for i in range(0, len(result_df), cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            if i + j < len(result_df):
                row_data = result_df.iloc[i + j]
                with cols[j]:
                    with st.container(border=True):
                        render_stock_card(row_data)
