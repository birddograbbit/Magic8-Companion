"""
Simplified configuration for Magic8-Companion recommendation engine.
Focuses on core settings without IB/Discord complexity.
"""
from pydantic_settings import BaseSettings
from typing import List


class SimplifiedSettings(BaseSettings):
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
    
    # Time zone
    timezone: str = "America/New_York"
    
    class Config:
        env_file = ".env"
        env_prefix = "M8C_"  # Magic8-Companion prefix


# Global settings instance
settings = SimplifiedSettings()
