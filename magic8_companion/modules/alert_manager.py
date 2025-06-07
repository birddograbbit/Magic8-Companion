import requests
from ..config import settings


def send_discord_alert(message: str):
    url = settings.discord_webhook
    if not url:
        print(message)
        return
    try:
        requests.post(url, json={"content": message})
    except Exception as e:
        print(f"Failed to send Discord alert: {e}")
