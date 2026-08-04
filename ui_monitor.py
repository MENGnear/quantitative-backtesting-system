# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : ui_monitor.py
# 程式版本 : ui_v1.10.3 (Phase 7: 雲端動態字典全面取代版)
#
# 📋 進版說明 (Version Notes):
#   1. [字典上雲] 匯入 market_repo，新增標的時同步寫入雲端字典，與頁面 B 共享記憶。
#   2. [格式統一] 實作 dynamic_format_option 與 format_del_option，全面對齊「代碼 + 名稱」。
#   3. [復原修復] 完整保留原版客製化的 HTML/CSS 卡片與市場分組排版邏輯。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 側邊欄渲染 (包含雲端字典覆寫與格式統一)
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
from core.repositories.market_repository import market_repo
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

    # 🔥 關鍵改造：從 Neon 資料庫載入雲端股票字典，覆寫原有的暫存參數
    db_tw_items = market_repo.get_dict_options('tw')
    db_us_items = market_repo.get_dict_options('us')
    
    # 建立雲端字典映射表供下拉選單格式化使用
    db_dict_map = {item['ticker']: item['display_name'] for item in db_tw_items + db_us_items}
    
    dynamic_tw_options = ["--- 請選擇 ---"] + [item['ticker'] for item in db_tw_items]
    dynamic_us_options = ["--- 請選擇 ---"] + [item['ticker'] for item in db_us_items]

    def dynamic_format_option(ticker):
        """通用格式化函數：統一資料庫選取下拉選單的顯示格式"""
        if ticker == "--- 請選擇 ---":
            return ticker
        clean_ticker = ticker.replace('.TW', '')
        name = str(db_dict_map.get(ticker, "")).strip()
        if not name or name == ticker or name == clean_ticker: return clean_ticker
        if name.startswith(clean_ticker): return name
        return f"{clean_ticker} {name}"

    monitor_items = monitor_repo.get_all_monitor_items()
    monitor_tickers = [item['ticker'] for item in monitor_items]
    monitor_map = {item['ticker']: item['display_name'] for item in monitor_items}
    
    def format_del_option(ticker):
        """刪除選單專用格式化函數"""
        if ticker == "--- 請選擇 ---":
            return ticker
        clean_ticker = ticker.replace('.TW', '')
        name = str(monitor_map.get(ticker, "")).strip()
        if not name or name == ticker or name == clean_ticker: return clean_ticker
        if name.startswith(clean_ticker): return name
        return f"{clean_ticker} {name}"

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
        
        # 替換為動態雲端字典與統一的格式化函數
        if "台灣" in market_choice:
            selected_db = st.selectbox("tw 資料庫選取", dynamic_tw_options, format_func=dynamic_format_option, key="sel_tw_val", on_change=on_sel_change)
        else:
            selected_db = st.selectbox("us 資料庫選取", dynamic_us_options, format_func=dynamic_format_option, key="sel_us_val", on_change=on_sel_change)
            
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
                        # 相容性保留：寫入舊版本地字典，避免其他未拔管模組報錯
                        if target_sym not in stock_dict or stock_dict[target_sym] != display_name:
                            stock_dict[target_sym] = display_name
                            save_stock_dict(stock_dict)
                            
                        # 🔥 關鍵寫入：永久寫入 Neon 雲端字典與監控母體表
                        market_repo.upsert_dict_item(target_sym, display_name, mkt)
                        monitor_repo.add_monitor_item(target_sym, display_name=display_name, market=mkt, thresholds=th_text, entry_prices=entry_text, exit_prices=exit_text)
                        st.cache_data.clear()
                        st.session_state.clear_input_flag = True
                        st.success(f"✅ {display_name} ({target_sym}) 新增成功！")
                        st.rerun()
                    else: st.error("❌ 查無此股票或獲取失敗，拒絕寫入！")

    with st.container(border=True):
        sidebar_header("🗑️", "移除監測標的")
        del_sym = st.selectbox("刪除目標", ["--- 請選擇 ---"] + monitor_tickers, format_func=format_del_option, key="del_a", label_visibility="collapsed")
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
