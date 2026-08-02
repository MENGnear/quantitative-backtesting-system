# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/postgres_adapter.py
# 程式版本 : v1.2.0 (Phase 7: 連線自動自癒升級版)
#
# 📋 進版說明 (Version Notes):
#   1. [自動重連] 針對 InterfaceError (連線關閉) 與 OperationalError (網路瞬斷) 加入攔截。
#   2. [無縫重試] 發現斷線時，自動銷毀舊連線並重連，重新執行失敗的 SQL，提升雲端韌性。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與類別宣告
#   - 2️⃣ 連線與佔位符轉換邏輯
#   - 3️⃣ 核心資料操作 (CRUD 介面 + 斷線重連防護)
#   - 4️⃣ 交易與連線狀態管理
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import psycopg2
import psycopg2.extras
import logging

class PostgresAdapter:
    def __init__(self, connection_url):
        self.connection_url = connection_url
        self.conn = None

# ==========================================================
# 2️⃣ 連線與佔位符轉換邏輯
# ==========================================================
    def connect(self):
        """建立或確保連線保持開啟狀態"""
        if self.conn is None or self.conn.closed != 0:
            try:
                self.conn = psycopg2.connect(self.connection_url)
            except Exception as e:
                logging.error(f"PostgreSQL 連線失敗: {e}")
                raise e

    def _convert_query(self, query):
        """將 SQLite 習慣的佔位符 '?' 自動轉換為 PostgreSQL 所需的 '%s'"""
        return query.replace("?", "%s")

# ==========================================================
# 3️⃣ 核心資料操作 (CRUD 介面 + 斷線重連防護)
# ==========================================================
    def execute(self, query, params=None):
        converted_query = self._convert_query(query)
        for attempt in range(2): # 允許重試 1 次
            try:
                self.connect()
                with self.conn.cursor() as cursor:
                    cursor.execute(converted_query, params or ())
                return
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                self.close() # 強制關閉壞掉的連線
                if attempt == 0:
                    logging.warning(f"⚠️ 資料庫連線中斷，正在自動重連 (execute)... 錯誤: {e}")
                    continue # 進入下一次迴圈進行重連
                raise e
            except Exception as e:
                self.rollback()
                logging.error(f"SQL 執行錯誤: {e} | 語法: {converted_query}")
                raise e

    def fetch_all(self, query, params=None):
        converted_query = self._convert_query(query)
        for attempt in range(2):
            try:
                self.connect()
                with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(converted_query, params or ())
                    return cursor.fetchall()
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                self.close()
                if attempt == 0:
                    logging.warning(f"⚠️ 資料庫連線中斷，正在自動重連 (fetch_all)... 錯誤: {e}")
                    continue
                raise e
            except Exception as e:
                self.rollback()
                logging.error(f"SQL 查詢錯誤 (fetch_all): {e} | 語法: {converted_query}")
                raise e

    def fetch_one(self, query, params=None):
        converted_query = self._convert_query(query)
        for attempt in range(2):
            try:
                self.connect()
                with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(converted_query, params or ())
                    return cursor.fetchone()
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                self.close()
                if attempt == 0:
                    logging.warning(f"⚠️ 資料庫連線中斷，正在自動重連 (fetch_one)... 錯誤: {e}")
                    continue
                raise e
            except Exception as e:
                self.rollback()
                logging.error(f"SQL 查詢錯誤 (fetch_one): {e} | 語法: {converted_query}")
                raise e

# ==========================================================
# 4️⃣ 交易與連線狀態管理
# ==========================================================
    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
