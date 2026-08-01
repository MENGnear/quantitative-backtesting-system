# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/postgres_adapter.py
# 程式版本 : v1.0.0 (Phase 7: 雲端資料庫支援)
#
# 📋 進版說明 (Version Notes):
#   1. [全新建立] 實作 PostgreSQL 連線轉接器，負責與 Neon 雲端資料庫溝通。
#   2. [相容設計] 自動將 SQLite 的佔位符 '?' 轉換為 PostgreSQL 的 '%s'，確保上層 Repository 完全免改寫。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 模組匯入與類別宣告
#   - 2️⃣ 連線與佔位符轉換邏輯
#   - 3️⃣ 核心資料操作 (CRUD 介面)
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
        """
        [相容性核心]
        將 SQLite 習慣的佔位符 '?' 自動轉換為 PostgreSQL 所需的 '%s'。
        如此一來，Repository 層的 SQL 語法無需做任何修改。
        """
        return query.replace("?", "%s")

# ==========================================================
# 3️⃣ 核心資料操作 (CRUD 介面)
# ==========================================================
    def execute(self, query, params=None):
        """執行非查詢類型的 SQL 指令 (INSERT, UPDATE, DELETE, CREATE)"""
        self.connect()
        converted_query = self._convert_query(query)
        with self.conn.cursor() as cursor:
            cursor.execute(converted_query, params or ())

    def fetch_all(self, query, params=None):
        """執行查詢並回傳所有結果，格式為 List[dict]"""
        self.connect()
        converted_query = self._convert_query(query)
        # 使用 RealDictCursor 確保回傳格式跟 SQLite Adapter 一樣是字典形式
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(converted_query, params or ())
            return cursor.fetchall()

    def fetch_one(self, query, params=None):
        """執行查詢並回傳單筆結果，格式為 dict"""
        self.connect()
        converted_query = self._convert_query(query)
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(converted_query, params or ())
            return cursor.fetchone()

# ==========================================================
# 4️⃣ 交易與連線狀態管理
# ==========================================================
    def commit(self):
        """提交資料庫交易"""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """回滾資料庫交易 (發生錯誤時)"""
        if self.conn:
            self.conn.rollback()

    def close(self):
        """關閉資料庫連線"""
        if self.conn:
            self.conn.close()
            self.conn = None
