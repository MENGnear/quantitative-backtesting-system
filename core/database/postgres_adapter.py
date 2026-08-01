# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/postgres_adapter.py
# 程式版本 : v1.1.0 (Phase 7: 自動修復交易鎖定版)
#
# 📋 進版說明 (Version Notes):
#   1. [穩健升級] 導入 Auto-Rollback (自癒) 機制。
#   2. [錯誤排解] 當任何 SQL 執行失敗時，自動清除連線的錯誤狀態，徹底解決
#      Streamlit 重新執行時發生 InFailedSqlTransaction 的「幽靈故障」。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與類別宣告
#   - 2️⃣ 連線與佔位符轉換邏輯
#   - 3️⃣ 核心資料操作 (CRUD 介面 + 防呆自動 Rollback)
#   - 4️⃣ 交易與連線狀態管理
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

# ==========================================================
# 1️⃣ 模組匯入與類別宣告
# ==========================================================
import psycopg2
import psycopg2.extras
import logging

class PostgresAdapter:
    def __init__(self, connection_url):
        """
        初始化 PostgreSQL 轉接器
        :param connection_url: 連線字串 (例如 Neon 提供的 URL)
        """
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
# 3️⃣ 核心資料操作 (CRUD 介面 + 防呆自動 Rollback)
# ==========================================================
    def execute(self, query, params=None):
        """執行非查詢類型的 SQL 指令 (INSERT, UPDATE, DELETE, CREATE)"""
        self.connect()
        converted_query = self._convert_query(query)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(converted_query, params or ())
        except Exception as e:
            # 🛡️ 關鍵修復：發生錯誤立刻 Rollback 清除髒狀態，避免波及後續查詢
            self.rollback()
            logging.error(f"SQL 執行錯誤: {e} | 語法: {converted_query}")
            raise e

    def fetch_all(self, query, params=None):
        """執行查詢並回傳所有結果，格式為 List[dict]"""
        self.connect()
        converted_query = self._convert_query(query)
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(converted_query, params or ())
                return cursor.fetchall()
        except Exception as e:
            self.rollback()
            logging.error(f"SQL 查詢錯誤 (fetch_all): {e} | 語法: {converted_query}")
            raise e

    def fetch_one(self, query, params=None):
        """執行查詢並回傳單筆結果，格式為 dict"""
        self.connect()
        converted_query = self._convert_query(query)
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(converted_query, params or ())
                return cursor.fetchone()
        except Exception as e:
            self.rollback()
            logging.error(f"SQL 查詢錯誤 (fetch_one): {e} | 語法: {converted_query}")
            raise e

# ==========================================================
# 4️⃣ 交易與連線狀態管理
# ==========================================================
    def commit(self):
        """提交資料庫交易"""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """回滾資料庫交易 (清除失敗鎖定)"""
        if self.conn:
            self.conn.rollback()

    def close(self):
        """關閉資料庫連線"""
        if self.conn:
            self.conn.close()
            self.conn = None
