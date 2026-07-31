# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : engines/strategy.py
# 程式版本 : engine_v1.2.0 (Pre-Phase 7: DDD 領域重構)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 正式從 core/engine_core.py 搬遷至 engines/strategy.py，確立為運算應用層。
#   2. [依賴反轉] 拔除回測母體的 sqlite3 直接連線，改由 strategy_repo 處理 CRUD 操作。
#   3. [防呆強化] 確保即使歷史資料不足，run_trend_momentum_analysis 仍回傳標準的空 DataFrame，保護 UI。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 基礎環境與倉儲對接
#   - 2️⃣ 核心技術指標運算池 (通用兵工廠)
#   - 3️⃣ 策略配方：趨勢動能評分系統 (Trend Momentum)
#   - 4️⃣ 引擎主程序 (匯總與排序)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import pandas as pd
import numpy as np
import logging
from core.repositories.strategy_repository import strategy_repo
from core.database.connection_factory import ConnectionFactory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================================
# 1️⃣ 基礎環境與倉儲對接
# ==========================================================
def get_backtest_targets():
    """透過 strategy_repo 獲取回測母體清單"""
    return strategy_repo.get_backtest_targets_df()

def get_historical_data(ticker):
    """
    提取指定股票的歷史 K 線。
    (註：此區塊透過 ConnectionFactory 取得連線，未來將重構至 market_repository)
    """
    db = ConnectionFactory.get_connection()
    query = "SELECT Date, Open, High, Low, Close, Volume FROM daily_price WHERE ticker = ? ORDER BY Date ASC"
    
    # 使用 fetch_all 並轉換為 DataFrame
    rows = db.fetch_all(query, (ticker,))
    if not rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(rows)
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
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    df['VMA5'] = df['Volume'].rolling(window=5).mean()
    
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD_Line'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
    
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
    
    if latest['MACD_Hist'] > 0: base_score += 15
    if latest['Close'] > latest['MA20']: base_score += 10
    if latest['MA20'] > prev_1['MA20']: base_score += 15
    if latest['MA20'] > latest['MA60']: base_score += 10
    if latest['Volume'] > (latest['VMA5'] * 1.5): base_score += 10

    divergence_flag = False
    
    if latest['RSI_6'] > latest['RSI_14'] and latest['RSI_14'] > 50:
        bonus_score += 5
        
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
    # 防呆：確保回傳的是標準空 DataFrame，而非 None
    if targets_df is None or targets_df.empty:
        return pd.DataFrame()
        
    results = []
    
    for _, row in targets_df.iterrows():
        ticker = row['ticker']
        name = row['display_name']
        
        hist_df = get_historical_data(ticker)
        if hist_df is None or hist_df.empty or len(hist_df) < 60:
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
