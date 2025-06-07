import pytest
import requests # Added as per plan
from unittest.mock import patch, MagicMock
from magic8_companion.modules.alert_manager import send_discord_alert
from magic8_companion.config import settings # To override settings for test

# Store original webhook URL to restore it later if needed, though typically not necessary for mocks
original_webhook_url = settings.discord_webhook

def test_send_discord_alert_success(monkeypatch):
    # Ensure settings.discord_webhook is set for this test
    monkeypatch.setattr(settings, 'discord_webhook', "https_dummy_webhook_url_com")

    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None # Simulate successful post
        mock_post.return_value = mock_response

        send_discord_alert("Test message")

        mock_post.assert_called_once_with(
            "https_dummy_webhook_url_com",
            json={"content": "Test message"}
        )
        mock_response.raise_for_status.assert_called_once()

def test_send_discord_alert_failure(monkeypatch, capsys):
    monkeypatch.setattr(settings, 'discord_webhook', "https_dummy_webhook_url_com")

    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException("Test HTTP error")

        send_discord_alert("Test message on failure")

        mock_post.assert_called_once()
        captured = capsys.readouterr()
        assert "Error sending Discord alert: Test HTTP error" in captured.out

def test_send_discord_alert_no_webhook_url(monkeypatch, capsys):
    # Set discord_webhook to None or empty string for this test
    monkeypatch.setattr(settings, 'discord_webhook', "")

    # We are not mocking requests.post here, as it shouldn't be called
    with patch('requests.post') as mock_post:
        send_discord_alert("Test message no webhook")

        mock_post.assert_not_called() # Ensure requests.post was not called
        captured = capsys.readouterr()
        assert "ALERT (Discord Webhook not configured): Test message no webhook" in captured.out

# It's good practice to clean up any monkeypatched settings if tests run in a shared context,
# though pytest usually isolates test runs.
# If using pytest fixtures for settings, this becomes cleaner.
@pytest.fixture(autouse=True)
def cleanup_settings():
    yield
    settings.discord_webhook = original_webhook_url # Restore original if it matters for other tests outside this file
