# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/sqlite_adapter.py
# 程式版本 : db_layer_v1.0.0 (Pre-Phase 7: Step 2 - Adapter)
#
# 📋 進版說明 (Version Notes):
#   1. [實作合約] 繼承並實作 DatabaseAdapter，封裝所有 sqlite3 的底層邏輯。
#   2. [資料淨化] 將 sqlite3.Row 自動轉換為標準 dict，確保上層 Repository 拿到純淨資料。
#   3. [執行緒安全] 設定 check_same_thread=False 避免 Streamlit 多執行緒報錯。
# ==========================================================

import sqlite3
from typing import Any, List, Dict, Tuple, Optional
from .base import DatabaseAdapter

class SQLiteAdapter(DatabaseAdapter):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self) -> None:
        """建立 SQLite 連線，並設定 row_factory 以利回傳字典格式"""
        if self.conn is None:
            # check_same_thread=False 確保 Streamlit 的 session 重載不會引發連線錯誤
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def disconnect(self) -> None:
        """安全關閉連線"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def commit(self) -> None:
        """提交交易"""
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        """回滾交易"""
        if self.conn:
            self.conn.rollback()

    def execute(self, query: str, params: Tuple = ()) -> None:
        """執行寫入/更新/刪除指令"""
        self.connect()
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
        finally:
            cursor.close()

    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """執行查詢並回傳多筆字典"""
        self.connect()
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            cursor.close()

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """執行查詢並回傳單筆字典"""
        self.connect()
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
