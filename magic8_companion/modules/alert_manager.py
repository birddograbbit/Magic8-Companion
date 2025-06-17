import requests
from ..unified_config import settings

def send_discord_alert(message: str):
    """
    Sends a message to the Discord webhook URL specified in settings.
    """
    if not settings.discord_webhook:
        print("ALERT (Discord Webhook not configured):", message)
        return

    payload = {"content": message}
    try:
        response = requests.post(settings.discord_webhook, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord alert: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending Discord alert: {e}")

if __name__ == '__main__':
    # Example usage (for testing purposes)
    # You would need to have your .env file configured with M8C_DISCORD_WEBHOOK
    # from ..config import Settings # To re-initialize if run directly for testing
    # settings_test = Settings() # Re-load for direct script run; careful with relative imports

    # This direct execution part is tricky due to relative imports.
    # It's better to test this by calling it from a higher-level script
    # or through integration tests.
    # If settings.discord_webhook:
    #     send_discord_alert("Test alert from alert_manager.py!")
    # else:
    #     print("Skipping example: M8C_DISCORD_WEBHOOK not set in .env for direct testing.")
    pass
