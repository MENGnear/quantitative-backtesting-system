# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/engine_core.py
# 程式版本 : engine_v1.1.0 (Phase 3: 通用核心引擎 - 指標積木化架構)
#
# 📋 進版說明 (Version Notes):
#   1. [架構] 正式定名為 engine_core.py，作為所有技術指標的「通用運算兵工廠」。
#   2. [策略] 內建第一套組合策略：「趨勢動能策略 (Trend Momentum)」，包含 Base 60 趨勢 + Bonus 20 動能背離。
#   3. [效能] 堅持純 Pandas 向量化運算 (Vectorized)，確保巨量歷史 K 線運算極速。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與資料庫對接
#   - 2️⃣ 核心技術指標運算池 (通用兵工廠)
#   - 3️⃣ 策略配方：趨勢動能評分系統 (Trend Momentum)
#   - 4️⃣ 引擎主程序 (匯總與排序)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import sqlite3
import pandas as pd
import numpy as np
import os
import logging

# 設定 Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 精準絕對路徑防護
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "stock_system.db")

# ==========================================================
# 1️⃣ 基礎環境與資料庫對接
# ==========================================================
def get_backtest_targets():
    """從資料庫獲取回測母體清單 (對接頁面 B)"""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT ticker, display_name FROM backtest_pool", conn)

def get_historical_data(ticker):
    """提取指定股票的歷史 K 線，並將 Date 設為時間序列索引"""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT Date, Open, High, Low, Close, Volume FROM daily_price WHERE ticker = ? ORDER BY Date ASC",
            conn, params=(ticker,)
        )
    if df.empty:
        return df
    
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df.dropna(inplace=True)
    return df

# ==========================================================
# 2️⃣ 核心技術指標運算池 (通用兵工廠)
# ==========================================================
def calculate_rsi(series, period=14):
    """計算 RSI (Wilder's Smoothing 算法)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_indicators(df):
    """批次計算所有技術指標積木"""
    # 均線系統
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['VMA5'] = df['Volume'].rolling(window=5).mean()
    
    # MACD 系統 (12, 26, 9)
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
    
    # RSI 系統
    df['RSI_6'] = calculate_rsi(df['Close'], 6)
    df['RSI_14'] = calculate_rsi(df['Close'], 14)
    df['RSI_24'] = calculate_rsi(df['Close'], 24)
    
    return df

# ==========================================================
# 3️⃣ 策略配方：趨勢動能評分系統 (Trend Momentum)
# ==========================================================
def evaluate_trend_momentum(df):
    """執行 Base 60 (趨勢) + Bonus 20 (動能背離) 評分邏輯"""
    if len(df) < 60:
        return None 
        
    latest = df.iloc[-1]
    prev_10 = df.iloc[-11] if len(df) >= 11 else df.iloc[0] 
    prev_1 = df.iloc[-2]
    
    base_score = 0
    bonus_score = 0
    
    # --- 主幹趨勢評分 (Base 60) ---
    if latest['MACD_Hist'] > 0: base_score += 15
    if latest['Close'] > latest['MA20']: base_score += 10
    if latest['MA20'] > prev_1['MA20']: base_score += 15
    if latest['MA20'] > latest['MA60']: base_score += 10
    if latest['Volume'] > (latest['VMA5'] * 1.5): base_score += 10

    # --- 動能震盪紅利 (Bonus 20) ---
    divergence_flag = False
    
    if latest['RSI_6'] > latest['RSI_14'] and latest['RSI_14'] > 50:
        bonus_score += 5
        
    # 底背離判定: 股價創近10日新低，但 RSI_14 反彈且小於 45
    if latest['Close'] < prev_10['Close'] and latest['RSI_14'] > prev_10['RSI_14'] and latest['RSI_14'] < 45:
        bonus_score += 15
        divergence_flag = True

    total_score = base_score + bonus_score
    
    return {
        'Close': round(latest['Close'], 2),
        'Base_Score': base_score,
        'Bonus_Score': bonus_score,
        'Total_Score': total_score,
        'Divergence': '✅' if divergence_flag else '-',
        'RSI_14': round(latest['RSI_14'], 1)
    }

# ==========================================================
# 4️⃣ 引擎主程序 (匯總與排序)
# ==========================================================
def run_trend_momentum_analysis():
    """執行趨勢動能策略，輸出結構化總表 DataFrame供 UI 渲染"""
    targets_df = get_backtest_targets()
    if targets_df.empty:
        return pd.DataFrame()
        
    results = []
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        name = row['display_name']
        
        hist_df = get_historical_data(ticker)
        if hist_df.empty or len(hist_df) < 60:
            continue
            
        hist_df = compute_indicators(hist_df)
        score_data = evaluate_trend_momentum(hist_df)
        
        if score_data:
            results.append({
                '代碼': ticker,
                '名稱': name,
                '收盤價': score_data['Close'],
                'RSI_14': score_data['RSI_14'],
                '底背離': score_data['Divergence'],
                '趨勢分(60)': score_data['Base_Score'],
                '紅利分(20)': score_data['Bonus_Score'],
                '總分': score_data['Total_Score']
            })
            
    if not results:
        return pd.DataFrame()
        
    result_df = pd.DataFrame(results)
    result_df.sort_values(by=['總分', '趨勢分(60)'], ascending=[False, False], inplace=True)
    result_df.reset_index(drop=True, inplace=True)
    
    return result_df
