# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : telegram_service.py
# 程式版本 : telegram_v1.0.0 (Phase 6.5: 通訊推播基礎設施)
#
# 📋 進版說明 (Version Notes):
#   1. [新增] 建立獨立的 Telegram 通訊服務模組 (基礎設施層)。
#   2. [架構] 導入非阻塞容錯與 Timeout (5秒) 防護，確保主程式穩定。
#   3. [修正] 移除 st.secrets，對齊 TW50 採用環境變數 (os.getenv) 讀取 Token 與 ID。
#
# 🏷️ 區塊說明 (Block Description):
#   - 1️⃣ 日誌系統初始化
#   - 2️⃣ Telegram 推播主程式 (TW50 Token/ID 機制)
#   - 3️⃣ 本機單元測試 (Unit Test)
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# ==========================================================

import os
import requests
import logging

# 1️⃣ 日誌系統初始化
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2️⃣ Telegram 推播主程式 (TW50 Token/ID 機制)
def send_telegram_message(message: str) -> bool:
    """
    將組裝好的文字訊息發送至指定的 Telegram 聊天室。
    對齊 TW50 標準：從系統環境變數讀取金鑰，完全解耦 Streamlit，支援 Pipeline 自動化。
    
    Args:
        message (str): 準備發送的警示文字內容
        
    Returns:
        bool: 發送成功回傳 True，失敗回傳 False
    """
    
    # 從環境變數讀取 Token 與 Chat ID
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # 防呆驗證：若找不到金鑰，則放棄推播，避免 API 報錯
    if not bot_token or not chat_id:
        logger.warning("⚠️ [Telegram] 尚未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，取消推播。")
        return False

    # 組裝 API 請求網址與封包
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",                # 支援基本 HTML 標籤如 <b>加粗</b>
        "disable_web_page_preview": True     # 關閉網址預覽，維持版面乾淨
    }

    # 執行發送並進行容錯攔截 (Timeout 嚴格限制為 5 秒)
    try:
        response = requests.post(url, json=payload, timeout=5)
        
        # 檢查 HTTP 狀態碼是否為 200 (成功)
        if response.status_code == 200:
            logger.info("✅ [Telegram] 訊息發送成功。")
            return True
        else:
            # 即使失敗也只印出錯誤，交由外層決定是否重試
            logger.error(f"❌ [Telegram] 發送失敗，狀態碼：{response.status_code}, 回應：{response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ [Telegram] API 請求超時 (Timeout > 5秒)，放棄本次推播。")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ [Telegram] 發生網路或連線例外錯誤：{e}")
        return False
    except Exception as e:
        logger.error(f"❌ [Telegram] 發生未預期的系統錯誤：{e}")
        return False

# 3️⃣ 本機單元測試 (Unit Test)
if __name__ == "__main__":
    print("啟動 Telegram 推播單元測試...")
    
    # 若本機未設定環境變數，可暫時在此行解除註解寫入測試 (上 GitHub 前記得刪除)
    # os.environ["TELEGRAM_BOT_TOKEN"] = "您的_BOT_TOKEN"
    # os.environ["TELEGRAM_CHAT_ID"] = "您的_CHAT_ID"
    
    test_msg = "🟢 <b>[QBS 系統測試]</b>\nTelegram 通訊模組已成功對齊 TW50 標準。"
    success = send_telegram_message(test_msg)
    
    if success:
        print("測試成功！請檢查您的 Telegram 手機 APP。")
    else:
        print("測試失敗！請檢查環境變數設定或網路連線。")
