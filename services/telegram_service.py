# ==========================================================
# ⭐⭐⭐⭐⭐⭐⭐⭐⭐⭐
# 專案名稱 : Quantitative Backtesting System (QBS)
# 檔案名稱 : telegram_service.py
# 程式版本 : tg_v1.1.0 (Phase 6.5: 單行極簡推播與共用組裝器)
#
# 📋 進版說明:
#   1. [新增] 參照 MON 系統，新增 build_qbs_tg_msg 單行極簡字串組裝器。
#   2. [修正] 嚴格落實無時間戳記之格式：🎯0050 | 📉$101.70 | -2.12%。
# ==========================================================
import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_telegram_message(message: str) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning("⚠️ [Telegram] 尚未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，取消推播。")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("✅ [Telegram] 訊息發送成功。")
            return True
        else:
            logger.error(f"❌ [Telegram] 發送失敗，狀態碼：{response.status_code}, 錯誤訊息：{response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ [Telegram] 請求超時或連線錯誤：{e}")
        return False

def build_qbs_tg_msg(name: str, price: float, delta_pct: float, is_manual: bool = False) -> str:
    """
    組裝極簡單行推播訊息，格式：🎯0050 | 📉$101.70 | -2.12%
    """
    # 決定圖示與正負號
    t_icon = "📈" if delta_pct >= 0 else "📉"
    sign = "+" if delta_pct > 0 else ""
    
    # 萃取代碼 (去除 .TW 等後綴以保持乾淨)
    clean_name = name.replace(".TW", "").split(" ")[0]
    
    # 組裝基本訊息 (絕對不加時間)
    msg = f"🎯{clean_name} | {t_icon}${price:,.2f} | {sign}{delta_pct:.2f}%"
    
    # 若為手動測試，則加上後綴
    if is_manual:
        msg += " | 🛠️手動"
        
    return msg
