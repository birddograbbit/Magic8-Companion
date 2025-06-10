"""
Simplified configuration for Magic8-Companion recommendation engine.
Focuses on core settings without IB/Discord complexity.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Simplified settings for recommendation engine."""
    
    # Core recommendation settings
    output_file_path: str = "data/recommendations.json"
    supported_symbols: List[str] = ["SPX", "SPY", "QQQ", "RUT"]
    checkpoint_times: List[str] = ["10:30", "11:00", "12:30", "14:45"]
    
    # Scoring thresholds
    min_recommendation_score: int = 70
    min_score_gap: int = 15
    
    # Market analysis settings
    use_mock_data: bool = True  # For testing without real market data
    mock_iv_percentile: float = 65.0
    mock_expected_range_pct: float = 0.008  # 0.8%
    
    # Live data settings (for when use_mock_data = False)
    market_data_provider: str = "yahoo"  # yahoo, ib, or polygon
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 2
    polygon_api_key: str = ""
    
    # Time zone
    timezone: str = "America/New_York"
    
    # Enhanced indicators
    enable_greeks: bool = False
    enable_advanced_gex: bool = False
    enable_volume_analysis: bool = False
    
    # IBKR specific settings
    use_ibkr_data: bool = False
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    ibkr_fallback_to_yahoo: bool = True
    
    # Logging settings
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/magic8_companion.log"
    log_file_max_size: int = 10485760
    log_file_backup_count: int = 5
    
    # Performance settings
    enable_caching: bool = True
    cache_expiry_minutes: int = 5
    enable_parallel_processing: bool = True
    max_workers: int = 4
    
    # Email settings
    smtp_port: int = 587
    
    # Greeks parameters
    greeks_risk_free_rate: float = 0.053
    greeks_dividend_yield: float = 0.012
    
    # GEX parameters
    gex_0dte_multiplier: float = 8.0
    gex_smoothing_window: int = 5
    
    # Volume analysis parameters
    volume_anomaly_threshold: float = 2.5
    volume_liquidity_min_oi: int = 100
    
    # Strategy thresholds
    butterfly_iv_threshold: int = 40
    iron_condor_iv_range: List[int] = [30, 80]
    vertical_min_iv: int = 50
    
    class Config:
        env_file = ".env"
        env_prefix = "M8C_"  # Magic8-Companion prefix


# Global settings instance
settings = Settings()
