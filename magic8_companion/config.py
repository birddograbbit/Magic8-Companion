from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Magic8 Integration
    magic8_source: str = "file"  # file, http, websocket
    magic8_file_path: str = "/data/magic8_output.json"
    magic8_url: str = ""
    magic8_poll_interval: int = 30

    # IB Connection
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 2

    # Alerts
    discord_webhook: str = ""

    # Risk Limits
    max_daily_loss: float = 5000
    max_position_loss: float = 2000

    # Scoring Thresholds
    min_recommendation_score: int = 70
    min_score_gap: int = 15

    class Config:
        env_file = ".env"

settings = Settings()
