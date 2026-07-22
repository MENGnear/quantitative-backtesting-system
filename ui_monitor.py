# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.3.0 (Phase 4.2: 終極復刻 MON 大盤與版面)
#
# 📋 進版說明 (Version Notes):
#   1. [版面重構] 徹底捨棄 st.columns，改用原生 HTML Flexbox，鎖定卡片寬度為 340px，完美還原 MON 比例。
#   2. [功能補回] 加入大盤指數 (^TWII, ^IXIC) 即時報價抓取，並依照台股/美股分類渲染獨立標題區塊。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 資料獲取與快取防護罩 (新增大盤指數)
#   - 2️⃣ 介面渲染主程式 (分群邏輯)
#   - 3️⃣ 市場群組渲染器 (包含標題與卡片 Flex 容器)
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
    quotes, alerts = engine_monitor.run_radar_scan()
    # 補抓台美股大盤指數
    indices = engine_monitor.fetch_realtime_quotes(['^TWII', '^IXIC'])
    quotes.update(indices)
    return quotes, alerts

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

    # 將標的分流為台股與美股
    tw_targets = targets_df[targets_df['market'] == 'tw']
    us_targets = targets_df[targets_df['market'] == 'us']

    # 渲染台股區塊
    if not tw_targets.empty:
        render_market_group("tw", tw_targets, quotes, alerts)
        
    # 渲染美股區塊
    if not us_targets.empty:
        # 如果上方有台股，加上一點間距
        if not tw_targets.empty:
            st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        render_market_group("us", us_targets, quotes, alerts)

# ==========================================================
# 3️⃣ 市場群組渲染器 (標題與 Flex 容器)
# ==========================================================
def render_market_group(market_type, targets_df, quotes, alerts):
    # 設定大盤標題參數
    if market_type == "tw":
        idx_ticker = "^TWII"
        idx_name = "tw 台灣股市 (Taiwan Market)"
        icon = "🔴 🇹🇼"
        bar_color = "#3b82f6" # 左側裝飾線條
    else:
        idx_ticker = "^IXIC"
        idx_name = "us 美國股市 (Nasdaq)"
        icon = "🟢 🇺🇸"
        bar_color = "#3b82f6"

    # 大盤報價字串處理
    idx_quote_html = ""
    if idx_ticker in quotes:
        q = quotes[idx_ticker]
        curr = q['current']
        chg_amt = q['change_amt']
        chg_pct = q['change_pct']
        
        if market_type == "tw":
            color = "#ef4444" if chg_amt > 0 else "#10b981"
            arrow = "↑" if chg_amt > 0 else "↓"
        else:
            color = "#10b981" if chg_amt > 0 else "#ef4444"
            arrow = "↑" if chg_amt > 0 else "↓"
            
        sign = "+" if chg_amt > 0 else ""
        idx_quote_html = f"""<span style="color: #38bdf8; margin-left: 10px;">{curr:,.2f}</span>
                             <span style="color: {color}; font-size: 1rem; margin-left: 8px;">{sign}{chg_amt:.2f} ({arrow}{abs(chg_pct):.2f}%)</span>"""
                             
    # 輸出大盤標題
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin: 10px 0 20px 0;">
        <div style="width: 4px; height: 22px; background-color: {bar_color}; margin-right: 12px;"></div>
        <div style="font-size: 1.25rem; font-weight: 800; color: #f8fafc; text-transform: uppercase;">
            {icon} {idx_name} {idx_quote_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 輸出卡片容器 (使用 Flexbox 解除 Streamlit 欄位限制)
    cards_html = "<div style='display: flex; flex-wrap: wrap; gap: 20px;'>"
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        clean_ticker = ticker.replace('.TW', '')
        clean_name = row['display_name']

        if ticker in quotes:
            q = quotes[ticker]
            curr = q['current']
            prev = q['prev']
            open_p = q['open']
            chg_amt = q['change_amt']
            chg_pct = q['change_pct']
            
            is_tw = market_type == "tw"
            
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
                badge_html = f"<div style='margin-top: 15px; background-color: {bg_color}; color: {text_color}; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 0.95rem; border: 1px solid {text_color}; box-shadow: inset 0 0 8px rgba(0,0,0,0.5);'>📈 觸發: {latest_alert['message']}</div>"

            th_raw = row['thresholds'] if pd.notna(row['thresholds']) and row['thresholds'] else "--"
            en_raw = row['entry_prices'] if pd.notna(row['entry_prices']) and row['entry_prices'] else "--"
            ex_raw = row['exit_prices'] if pd.notna(row['exit_prices']) and row['exit_prices'] else "--"

            # 🚨 綁死寬度 width: 340px; 嚴格對齊 MON 尺寸
            cards_html += f"""
            <div style="width: 340px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{clean_ticker} {clean_name}</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #38bdf8; margin-bottom: 16px;">${curr:.2f}</div>
                <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px;">
                    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">昨收： <span style="color: #f8fafc; margin-left: 5px;">${prev:.2f}</span></div>
                    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">開盤： <span style="color: #f8fafc; margin-left: 5px;">${open_p:.2f}</span></div>
                    <div style="font-size: 0.95rem; color: #94a3b8; font-weight: 600;">漲幅： <span style="color: {text_color}; margin-left: 5px;">{chg_str}</span></div>
                </div>
                <div style="border-top: 1px dashed #475569; padding-top: 12px; text-align: center; color: #64748b; font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">門檻: {th_raw}% | 進場: ${en_raw} | 出場: ${ex_raw}</div>
                {badge_html}
            </div>
            """
        else:
            cards_html += f"""
            <div style="width: 340px; background-color: #1c191b; border: 1px solid #3d2a2e; border-radius: 8px; padding: 20px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{clean_ticker} {clean_name}</div>
                <div style="color: #64748b; font-size: 1.1rem; margin-top: 20px;">資料讀取中...</div>
            </div>
            """
            
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
