# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : core/database/base.py
# 程式版本 : db_layer_v1.0.0 (Pre-Phase 7: Step 1)
#
# 📋 進版說明 (Version Notes):
#   1. [架構重構] 定義 DatabaseAdapter 抽象基底類別 (Abstract Base Class)。
#   2. [依賴反轉] 強制所有資料庫實作 (SQLite, PostgreSQL) 必須遵循標準介面。
#   3. [交易防護] 定義明確的 commit() 與 rollback()，確保未來大規模寫入時的資料一致性。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 抽象介面定義與連線生命週期
#   - 2️⃣ 查詢與執行標準介面
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import abc
from typing import Any, List, Dict, Tuple, Optional

class DatabaseAdapter(abc.ABC):
    """
    資料庫轉接器抽象介面 (The Interface Contract)
    
    所有具體的資料庫轉接器 (如 SQLiteAdapter, PostgresAdapter) 
    都必須繼承此類別，並實作以下所有的抽象方法。
    這確保了上層的 Repository 永遠只需要面對統一的介面，達到徹底的依賴解耦。
    """
    
    # ==========================================================
    # 1️⃣ 抽象介面定義與連線生命週期
    # ==========================================================
    @abc.abstractmethod
    def connect(self) -> None:
        """建立資料庫連線"""
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """關閉資料庫連線"""
        pass

    @abc.abstractmethod
    def commit(self) -> None:
        """提交 (Commit) 當前交易 (Transaction)"""
        pass

    @abc.abstractmethod
    def rollback(self) -> None:
        """回滾 (Rollback) 當前交易，用於發生異常時保護資料"""
        pass

    # ==========================================================
    # 2️⃣ 查詢與執行標準介面
    # ==========================================================
    @abc.abstractmethod
    def execute(self, query: str, params: Tuple = ()) -> None:
        """
        執行單一 SQL 語法 (適用於 INSERT, UPDATE, DELETE)
        
        Args:
            query (str): SQL 語法字串
            params (Tuple): 綁定變數，預防 SQL Injection
        """
        pass

    @abc.abstractmethod
    def fetch_all(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        執行 SQL 查詢並回傳所有結果
        
        Args:
            query (str): SQL 查詢語法
            params (Tuple): 綁定變數
            
        Returns:
            List[Dict[str, Any]]: 包含多筆結果的列表，每一筆結果必須是「欄位名稱: 值」的字典結構
        """
        pass

    @abc.abstractmethod
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """
        執行 SQL 查詢並回傳單一筆結果
        
        Args:
            query (str): SQL 查詢語法
            params (Tuple): 綁定變數
            
        Returns:
            Optional[Dict[str, Any]]: 單筆結果字典，若查無資料則回傳 None
        """
        pass
