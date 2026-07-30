# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.10.2 (Pre-Phase 7: Step 4 - 倉儲層替換)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 導入 render_sidebar，承接從 QBS_app 剝離的側邊欄業務邏輯。
#   2. [依賴解耦] 徹底拔除 core.db_manager，改用核心倉儲 monitor_repo 進行資料進出。
#   3. [復原修復] 完整保留原版 v1.9.6 中客製化的 HTML/CSS 卡片與市場分組 (TW/US) 排版邏輯。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 側邊欄渲染 (Micro-Frontend)
#   - 2️⃣ 資料獲取與動態快取防護
#   - 3️⃣ 介面渲染主程式 (維持原樣)
#   - 4️⃣ 市場群組渲染器 (維持原樣)
#   - 5️⃣ 系統工具組與推播測試元件
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import streamlit as st
import pandas as pd
import textwrap
import pytz
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime
from core import engine_monitor
from core.repositories.monitor_repository import monitor_repo
from services.telegram_service import send_telegram_message, build_qbs_tg_msg

# ==========================================================
# 1️⃣ 側邊欄渲染 (Micro-Frontend)
# ==========================================================
def render_sidebar(stock_dict, save_stock_dict, tw_options, us_options, format_tw_option, sidebar_header):
    if "sel_tw_val" not in st.session_state: st.session_state.sel_tw_val = "--- 請選擇 ---"
    if "sel_us_val" not in st.session_state: st.session_state.sel_us_val = "--- 請選擇 ---"
    if "manual_sym_val" not in st.session_state: st.session_state.manual_sym_val = ""
    if "clear_input_flag" not in st.session_state: st.session_state.clear_input_flag = False

    def on_sel_change(): st.session_state.manual_sym_val = ""
    def on_manual_change():
        if st.session_state.manual_sym_val.strip() != "":
            st.session_state.sel_tw_val = "--- 請選擇 ---"
            st.session_state.sel_us_val = "--- 請選擇 ---"

    monitor_items = monitor_repo.get_all_monitor_items()
    monitor_tickers = [item['ticker'] for item in monitor_items]
    
    monitor_map = {}
    for item in monitor_items:
        t = item['ticker']
        ct = t.replace('.TW', '')
        dn = str(item['display_name']).strip()
        if not dn or dn == t or dn == ct: monitor_map[t] = f"{ct}"
        elif dn.startswith(ct): monitor_map[t] = f"{dn}"
        else: monitor_map[t] = f"{ct} {dn}"

    with st.container(border=True):
        sidebar_header("▶️", "執行股票監測")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("開始", use_container_width=True, key="start_mon"): 
                if not st.session_state.monitoring:
                    st.session_state.monitoring = True
                    now_tpe = datetime.now(pytz.timezone('Asia/Taipei'))
                    prefix = "TW" if 6 <= now_tpe.hour <= 18 else "US"
                    send_telegram_message(f"🎯{prefix} | 🟢開始監測")
        with col_btn2:
            if st.button("暫停", use_container_width=True, key="stop_mon"): 
                if st.session_state.monitoring:
                    st.session_state.monitoring = False
                    now_tpe = datetime.now(pytz.timezone('Asia/Taipei'))
                    prefix = "TW" if 6 <= now_tpe.hour <= 18 else "US"
                    send_telegram_message(f"🎯{prefix} | 🟡暫停監測")
                    
        if st.session_state.monitoring: st.success("🟢 即時監測中")
        else: st.info("🟡 監測暫停中")

    with st.container(border=True):
        sidebar_header("➕", "新增即時監控")
        market_choice = st.radio("選擇市場", ["tw 台灣", "us 美國"], horizontal=True, key="mkt_a")
        
        if "台灣" in market_choice:
            selected_db = st.selectbox("tw 資料庫選取", tw_options, format_func=format_tw_option, key="sel_tw_val", on_change=on_sel_change)
        else:
            selected_db = st.selectbox("us 資料庫選取", us_options, format_func=lambda x: stock_dict.get(x, x) if x != "--- 請選擇 ---" else x, key="sel_us_val", on_change=on_sel_change)
            
        if st.session_state.clear_input_flag:
            st.session_state.manual_sym_val = ""
            st.session_state.clear_input_flag = False
            
        new_sym = st.text_input("或 手動輸入代碼", placeholder="例: 6531", key="manual_sym_val", on_change=on_manual_change).strip().upper()
        
        st.markdown("<div style='font-size:0.85rem; color:#94a3b8; margin-bottom:5px;'>監控條件設定：</div>", unsafe_allow_html=True)
        th_text = st.text_input("提醒門檻 (%)", value="", placeholder="例: 5, 10", key="th_a", label_visibility="collapsed")
        entry_text = st.text_input("進場提醒 ($)", value="", placeholder="進場價 (例: 150)", key="entry_a", label_visibility="collapsed")
        exit_text = st.text_input("出場提醒 ($)", value="", placeholder="出場價 (例: 190)", key="exit_a", label_visibility="collapsed")
        
        if st.button("確認新增", use_container_width=True, key="btn_add_a"):
            if not (th_text.strip() or entry_text.strip() or exit_text.strip()):
                st.warning("⚠️ 請至少輸入一項監控條件！")
            else:
                target_sym = new_sym if new_sym else (selected_db if selected_db != "--- 請選擇 ---" else None)
                if target_sym:
                    mkt = "tw" if "台灣" in market_choice else "us"
                    if mkt == "tw" and not target_sym.endswith(".TW"): target_sym += ".TW"
                    if mkt == "us": target_sym = target_sym.replace(".TW", "")
                    
                    display_name = ""
                    is_valid = False
                    
                    with st.spinner(f"🔍 驗證標的與獲取名稱中..."):
                        try:
                            if mkt == "tw":
                                res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_sym}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                                soup = BeautifulSoup(res.text, 'html.parser')
                                title = soup.find('title').text
                                if " - " in title:
                                    clean_title = title.split(" - ")[0].split("(")[0]
                                    name_part = clean_title.replace(target_sym.replace('.TW', ''), '').strip()
                                    if name_part: display_name = name_part; is_valid = True
                            else:
                                fi = yf.Ticker(target_sym).fast_info
                                if fi.last_price is not None: display_name = target_sym; is_valid = True
                        except: pass
                    
                    if is_valid:
                        if target_sym not in stock_dict or stock_dict[target_sym] != display_name:
                            stock_dict[target_sym] = display_name
                            save_stock_dict(stock_dict)
                        monitor_repo.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                        st.cache_data.clear()
                        st.session_state.clear_input_flag = True
                        st.success(f"✅ {display_name} ({target_sym}) 新增成功！")
                        st.rerun()
                    else: st.error("❌ 查無此股票或獲取失敗，拒絕寫入！")

    with st.container(border=True):
        sidebar_header("🗑️", "移除監測標的")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=lambda x: monitor_map.get(x, x) if x != "--- 請選擇 ---" else x, key="del_a", label_visibility="collapsed")
        if st.button("確認刪除", use_container_width=True, key="btn_del_a"):
            if del_sym != "--- 請選擇 ---":
                monitor_repo.remove_monitor_item(del_sym)
                st.cache_data.clear()
                st.success(f"🗑️ 已移除標的")
                st.rerun()

    with st.container(border=True):
        sidebar_header("⏱️", "系統運行狀態")
        refresh_sec_a = st.slider("刷新頻率(秒)", 5, 60, 30, key="refresh_a")
        if st.button("🔄 手動刷新", use_container_width=True, key="manual_ref_a"): 
            st.cache_data.clear()
            st.rerun()

# ==========================================================
# 2️⃣ 資料獲取
# ==========================================================
def get_realtime_radar_data(tickers_tuple, is_monitoring):
    quotes, alerts = engine_monitor.run_radar_scan(is_monitoring)
    indices = engine_monitor.fetch_realtime_quotes(['^TWII', '^IXIC'])
    quotes.update(indices)
    return quotes, alerts

# ==========================================================
# 3️⃣ 介面渲染主程式
# ==========================================================
def render_radar_dashboard():
    st.markdown("### 📡 實戰雷達監測 (Execution Battlefield)")
    
    targets_df = engine_monitor.get_monitor_targets()
    if targets_df.empty:
        st.info("💡 實戰彈藥庫目前為空，請先從左側「新增即時監控」寫入標的。")
        return

    current_tickers = tuple(targets_df['ticker'].tolist())
    
    is_monitoring = st.session_state.get('monitoring', False)

    with st.spinner("📡 正在擷取即時報價與掃描防線..."):
        quotes, alerts = get_realtime_radar_data(current_tickers, is_monitoring)

    tw_targets = targets_df[targets_df['market'] == 'tw']
    us_targets = targets_df[targets_df['market'] == 'us']

    if not tw_targets.empty:
        render_market_group("tw", tw_targets, quotes, alerts)
        
    if not us_targets.empty:
        if not tw_targets.empty:
            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        render_market_group("us", us_targets, quotes, alerts)

# ==========================================================
# 4️⃣ 市場群組渲染器
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
# 5️⃣ 系統工具組與推播測試元件
# ==========================================================
def render_telegram_manual_test_ui():
    with st.sidebar.expander("🛠️ 系統推播測試", expanded=False):
        if st.button("發送目前小卡狀態", type="primary", use_container_width=True):
            with st.spinner("發送中，請稍候..."):
                now_tpe = datetime.now(pytz.timezone('Asia/Taipei'))
                is_tw_time = 6 <= now_tpe.hour <= 18
                
                target_idx = "^TWII" if is_tw_time else "^IXIC"
                idx_name = "TW" if is_tw_time else "US"
                
                msg_lines = []
                
                idx_quotes = engine_monitor.fetch_realtime_quotes([target_idx])
                if target_idx in idx_quotes:
                    q = idx_quotes[target_idx]
                    msg_lines.append(build_qbs_tg_msg(idx_name, q['current'], q['change_pct'], is_manual=True))
                else:
                    msg_lines.append(f"🎯{idx_name} | ⚠️大盤獲取失敗 | 🛠️手動")
                
                targets_df = engine_monitor.get_monitor_targets()
                if not targets_df.empty:
                    if is_tw_time:
                        targets_df = targets_df[targets_df['ticker'].str.contains(r'\.TW', na=False, regex=True)]
                    else:
                        targets_df = targets_df[~targets_df['ticker'].str.contains(r'\.TW', na=False, regex=True)]
                    
                    if not targets_df.empty:
                        current_tickers = targets_df['ticker'].tolist()
                        quotes = engine_monitor.fetch_realtime_quotes(current_tickers)
                        
                        for _, row in targets_df.iterrows():
                            ticker = row['ticker']
                            clean_name = ticker.replace(".TW", "")
                                
                            if ticker in quotes:
                                q = quotes[ticker]
                                line = build_qbs_tg_msg(clean_name, q['current'], q['change_pct'], is_manual=True)
                                msg_lines.append(line)
                                
                final_msg = "\n".join(msg_lines)
                success = send_telegram_message(final_msg)
                
                if success:
                    st.success("✅ 手動推播發送成功！")
                else:
                    st.error("❌ 發送失敗，請檢查金鑰設定或網路連線。")
