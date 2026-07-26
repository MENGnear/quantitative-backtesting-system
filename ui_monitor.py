# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.9.3 (Phase 6.5: 手動推播強制大盤置頂組合)
#
# 📋 進版說明 (Version Notes):
#   1. [快取解套] 將 tickers_tuple 導入 st.cache_data 裝飾器，確保每次新增股票時動態破除舊快取，秒速顯示新小卡。
#   2. [顯示優化] 強化標題智慧去重邏輯，徹底根除「NVDA NVDA」等重複字眼。
#   3. [功能升級] (v1.9.3) 修改手動推播邏輯：強制發送「純大盤」或「大盤+小股組合」，且每行皆附帶手動標籤。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 資料獲取與動態快取防護
#   - 2️⃣ 介面渲染主程式
#   - 3️⃣ 市場群組渲染器 
#   - 4️⃣ 系統工具組與推播測試元件 (🔥 邏輯大幅升級)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import pandas as pd
import textwrap
import pytz
from datetime import datetime
from core import engine_monitor
from services.telegram_service import send_telegram_message, build_qbs_tg_msg

# ==========================================================
# 1️⃣ 資料獲取與動態快取防護
# ==========================================================
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_radar_data(tickers_tuple):
    quotes, alerts = engine_monitor.run_radar_scan()
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
        st.info("💡 實戰彈藥庫目前為空，請先從左側「新增即時監控」寫入標的。")
        return

    current_tickers = tuple(targets_df['ticker'].tolist())

    with st.spinner("📡 正在擷取即時報價與掃描防線..."):
        quotes, alerts = get_cached_radar_data(current_tickers)

    tw_targets = targets_df[targets_df['market'] == 'tw']
    us_targets = targets_df[targets_df['market'] == 'us']

    if not tw_targets.empty:
        render_market_group("tw", tw_targets, quotes, alerts)
        
    if not us_targets.empty:
        if not tw_targets.empty:
            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        render_market_group("us", us_targets, quotes, alerts)

# ==========================================================
# 3️⃣ 市場群組渲染器
# ==========================================================
def render_market_group(market_type, targets_df, quotes, alerts):
    if market_type == "tw":
        idx_ticker = "^TWII"
        idx_name = "tw 台灣股市 (Taiwan Market)"
        icon = "🔴"
        bar_color = "#3b82f6"
    else:
        idx_ticker = "^IXIC"
        idx_name = "us 美國股市 (Nasdaq)"
        icon = "🟢"
        bar_color = "#3b82f6"

    idx_quote_html = ""
    if idx_ticker in quotes:
        q = quotes[idx_ticker]
        curr = q['current']
        chg_amt = q['change_amt']
        chg_pct = q['change_pct']
        
        if market_type == "tw":
            color = "#ef4444" if chg_amt > 0 else "#10b981"
        else:
            color = "#10b981" if chg_amt > 0 else "#ef4444"
            
        arrow = "↑" if chg_amt > 0 else "↓"
        sign = "+" if chg_amt > 0 else ""
        idx_quote_html = f"""<span style="color: #38bdf8; margin-left: 10px;">{curr:,.2f}</span> <span style="color: {color}; font-size: 1rem; margin-left: 8px;">{sign}{chg_amt:.2f} ({arrow}{abs(chg_pct):.2f}%)</span>"""
                             
    header_html = textwrap.dedent(f"""
    <div style="display: flex; align-items: center; margin: 10px 0 20px 0;">
        <div style="width: 4px; height: 22px; background-color: {bar_color}; margin-right: 12px;"></div>
        <div style="font-size: 1.25rem; font-weight: 800; color: #f8fafc;">
            {icon} {idx_name} {idx_quote_html}
        </div>
    </div>
    """).strip()
    st.markdown(header_html, unsafe_allow_html=True)

    cards_html = "<div style='display: flex; flex-wrap: wrap; gap: 18px;'>"
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        clean_ticker = ticker.replace('.TW', '')
        clean_name = str(row['display_name']).strip()

        if not clean_name or clean_name == ticker or clean_name == clean_ticker:
            display_title = clean_ticker
        elif clean_name.startswith(clean_ticker):
            display_title = clean_name
        else:
            display_title = f"{clean_ticker} {clean_name}"

        if ticker in quotes:
            q = quotes[ticker]
            curr = q['current']
            prev = q['prev']
            open_p = q['open']
            chg_amt = q['change_amt']
            chg_pct = q['change_pct']
            
            is_tw = market_type == "tw"
            
            if chg_amt > 0:
                sign = "+"
                if is_tw: 
                    bg_color = "#2b1819" ; border_color = "#5a262c" ; text_color = "#ef4444" 
                else:     
                    bg_color = "#18241d" ; border_color = "#1f4738" ; text_color = "#10b981"
            elif chg_amt < 0:
                sign = ""
                if is_tw: 
                    bg_color = "#18241d" ; border_color = "#1f4738" ; text_color = "#10b981"
                else:     
                    bg_color = "#2b1819" ; border_color = "#5a262c" ; text_color = "#ef4444"
            else:
                sign = ""
                bg_color = "#1c191b" ; border_color = "#3d2a2e" ; text_color = "#cbd5e1"
                
            chg_str = f"{sign}{chg_amt:.2f} ({sign}{chg_pct:.2f}%)"
            
            badge_html = ""
            ticker_alerts = [a for a in alerts if a['ticker'] == ticker]
            if ticker_alerts:
                badge_html = f"<div style='margin-top: 15px; background-color: {bg_color}; color: {text_color}; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 0.95rem; border: 1px solid {text_color}; box-shadow: inset 0 0 8px rgba(0,0,0,0.5);'>📈 觸發: {ticker_alerts[0]['message']}</div>"

            th_raw = row['thresholds'] if pd.notna(row['thresholds']) and row['thresholds'] else "--"
            en_raw = row['entry_prices'] if pd.notna(row['entry_prices']) and row['entry_prices'] else "--"
            ex_raw = row['exit_prices'] if pd.notna(row['exit_prices']) and row['exit_prices'] else "--"

            card_html = textwrap.dedent(f"""
            <div style="width: 280px; min-width: 280px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; justify-content: space-between;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
            <div style="font-size: 2.1rem; font-weight: 800; color: #38bdf8; margin-bottom: 16px;">${curr:.2f}</div>
            <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px;">
            <div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">昨收： <span style="color: #f8fafc; margin-left: 5px;">${prev:.2f}</span></div>
            <div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">開盤： <span style="color: #f8fafc; margin-left: 5px;">${open_p:.2f}</span></div>
            <div style="font-size: 0.9rem; color: #94a3b8; font-weight: 600;">漲幅： <span style="color: {text_color}; margin-left: 5px;">{chg_str}</span></div>
            </div>
            <div style="border-top: 1px dashed #475569; padding-top: 12px; text-align: center; color: #64748b; font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">門檻: {th_raw}% | 進場: ${en_raw} | 出場: ${ex_raw}</div>
            {badge_html}
            </div>
            """).strip()
            
            cards_html += card_html
        else:
            card_loading = textwrap.dedent(f"""
            <div style="width: 280px; min-width: 280px; background-color: #1c191b; border: 1px solid #3d2a2e; border-radius: 8px; padding: 18px;">
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{display_title}</div>
            <div style="color: #64748b; font-size: 1rem; margin-top: 20px;">資料讀取中...</div>
            </div>
            """).strip()
            cards_html += card_loading
            
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

# ==========================================================
# 4️⃣ 系統工具組與推播測試元件 (🔥 邏輯大幅升級)
# ==========================================================
def render_telegram_manual_test_ui():
    """
    實作手動推播的智慧判斷 (V1.9.3 升級)：
    1. 強制第一行發送當下時區的大盤報價。
    2. 如果有小卡，依序接在大盤下方。
    3. 全系列字串組合後一次發送，並統一加上 🛠️手動 標籤。
    """
    with st.container(border=True):
        st.markdown("### 🛠️ 手動測試推播")
        
        if st.button("發送目前小卡狀態", type="primary", use_container_width=True):
            with st.spinner("發送中，請稍候..."):
                now_tpe = datetime.now(pytz.timezone('Asia/Taipei'))
                is_tw_time = 6 <= now_tpe.hour <= 18
                
                target_idx = "^TWII" if is_tw_time else "^IXIC"
                idx_name = "TW" if is_tw_time else "US"
                
                msg_lines = []
                
                # 步驟 1: 永遠先擷取並組裝大盤資訊
                idx_quotes = engine_monitor.fetch_realtime_quotes([target_idx])
                if target_idx in idx_quotes:
                    q = idx_quotes[target_idx]
                    msg_lines.append(build_qbs_tg_msg(idx_name, q['current'], q['change_pct'], is_manual=True))
                else:
                    msg_lines.append(f"🎯{idx_name} | ⚠️大盤獲取失敗 | 🛠️手動")
                
                # 步驟 2: 檢查並附加所有小卡資訊
                targets_df = engine_monitor.get_monitor_targets()
                if not targets_df.empty:
                    quotes, _ = engine_monitor.run_radar_scan() # 獲取小卡最新報價
                    for _, row in targets_df.iterrows():
                        ticker = row['ticker']
                        clean_name = str(row['display_name']).strip()
                        if not clean_name or clean_name == ticker:
                            clean_name = ticker.replace(".TW", "")
                            
                        if ticker in quotes:
                            q = quotes[ticker]
                            line = build_qbs_tg_msg(clean_name, q['current'], q['change_pct'], is_manual=True)
                            msg_lines.append(line)
                            
                # 步驟 3: 將所有陣列元素用換行符號合併並發送
                final_msg = "\n".join(msg_lines)
                success = send_telegram_message(final_msg)
                
                if success:
                    st.success("✅ 手動推播發送成功！")
                else:
                    st.error("❌ 發送失敗，請檢查金鑰設定或網路連線。")
