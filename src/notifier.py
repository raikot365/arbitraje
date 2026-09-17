import os
import time
import requests
import threading
import logging
from dotenv import load_dotenv
from src.settings import load_settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self._alertas_enviadas = {}
        self.reload_config()

    def reload_config(self):
        load_dotenv()
        settings = load_settings()
        self.telegram_token = settings.get("telegram_token") or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = settings.get("chat_id") or os.getenv("CHAT_ID")

    def _send_message(self, msg):
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            requests.post(url, data={"chat_id": self.chat_id, "text": msg}, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}")

    def process_alerts(self, alerts, cooldown_secs, only_best=False):
        """
        alerts is a list of dicts: {"cat": str, "ex1": str, "ex2": str, "ask": float, "bid": float, "gain": float}
        """
        if not self.telegram_token or not self.chat_id:
            return

        current_time = time.time()

        if only_best:
            best_by_cat = {}
            for alert in alerts:
                cat = alert["cat"]
                if cat not in best_by_cat or alert["gain"] > best_by_cat[cat]["gain"]:
                    best_by_cat[cat] = alert
            alerts_to_process = list(best_by_cat.values())
        else:
            alerts_to_process = alerts

        for alert in alerts_to_process:
            cat, ex1, ex2 = alert["cat"], alert["ex1"], alert["ex2"]
            gain, ask, bid = alert["gain"], alert["ask"], alert["bid"]
            
            key = (ex1, ex2, cat)
            if current_time - self._alertas_enviadas.get(key, 0) > cooldown_secs:
                msg = f"🔥 [{cat}] {gain:.2f}%\n🛒 {ex1.upper()}: {ask:,.2f}\n💰 {ex2.upper()}: {bid:,.2f}"
                threading.Thread(target=self._send_message, args=(msg,), daemon=True).start()
                self._alertas_enviadas[key] = current_time
