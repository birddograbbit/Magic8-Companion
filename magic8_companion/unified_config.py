"""
Unified configuration for Magic8-Companion recommendation engine.
Consolidates config.py and config_simplified.py into one flexible system.
"""
from pydantic_settings import BaseSettings
from typing import List
from enum import Enum


class SystemComplexity(Enum):
    """System complexity modes."""
    SIMPLE = "simple"      # Minimal features, basic functionality
    STANDARD = "standard"  # Full features for production
    ENHANCED = "enhanced"  # All features including advanced indicators


class Settings(BaseSettings):
    """Unified settings that replaces both config.py and config_simplified.py."""
    
    # === CORE SYSTEM SETTINGS ===
    
    # System complexity mode
    system_complexity: str = "standard"  # simple, standard, enhanced
    
    # Core recommendation settings
    output_file_path: str = "data/recommendations.json"
    supported_symbols: List[str] = ["SPX", "SPY", "QQQ", "RUT"]
    checkpoint_times: List[str] = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30"]
    
    # Scoring thresholds - MADE MORE LENIENT
    min_recommendation_score: int = 60  # Down from 70
    min_score_gap: int = 10  # Down from 15
    
    # === MARKET DATA SETTINGS ===
    
    # Market analysis settings (simplified mode uses mock data)
    use_mock_data: bool = False  # Set to true for testing
    mock_iv_percentile: float = 65.0
    mock_expected_range_pct: float = 0.008  # 0.8%
    
    # Live data provider selection
    market_data_provider: str = "yahoo"  # yahoo, ib, or polygon
    
    # Time zone
    timezone: str = "America/New_York"
    
    # === INTERACTIVE BROKERS SETTINGS ===
    
    # Basic IB settings
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 2
    
    # Advanced IBKR settings (only used in standard/enhanced modes)
    use_ibkr_data: bool = False
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1
    ibkr_fallback_to_yahoo: bool = True
    
    # === API KEYS ===
    
    polygon_api_key: str = ""
    
    # === ENHANCED INDICATORS (only used in enhanced mode) ===
    
    enable_greeks: bool = False
    enable_advanced_gex: bool = False
    enable_volume_analysis: bool = False
    
    # === LOGGING CONFIGURATION ===
    
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/magic8_companion.log"
    log_file_max_size: int = 10485760
    log_file_backup_count: int = 5

    # === ALERT SETTINGS ===
    
    discord_webhook: str = ""
    
    # === PERFORMANCE SETTINGS ===
    
    enable_caching: bool = True
    cache_expiry_minutes: int = 5
    enable_parallel_processing: bool = True
    max_workers: int = 4
    
    # === EMAIL SETTINGS ===
    
    smtp_port: int = 587
    
    # === GREEKS PARAMETERS (enhanced mode only) ===
    
    greeks_risk_free_rate: float = 0.053
    greeks_dividend_yield: float = 0.012
    
    # === GEX PARAMETERS (enhanced mode only) ===
    
    gex_0dte_multiplier: float = 8.0
    gex_smoothing_window: int = 5
    
    # === VOLUME ANALYSIS PARAMETERS (enhanced mode only) ===
    
    volume_anomaly_threshold: float = 2.5
    volume_liquidity_min_oi: int = 100
    
    # === STRATEGY THRESHOLDS - MADE MORE LENIENT ===
    
    butterfly_iv_threshold: int = 50  # Up from 40
    iron_condor_iv_range: List[int] = [25, 85]  # Expanded from [30, 80]
    vertical_min_iv: int = 40  # Down from 50
    
    # === CONFIGURATION PROPERTIES ===
    
    @property
    def is_simple_mode(self) -> bool:
        """Check if running in simple mode."""
        return self.system_complexity == "simple"
    
    @property
    def is_standard_mode(self) -> bool:
        """Check if running in standard mode."""
        return self.system_complexity == "standard"
    
    @property
    def is_enhanced_mode(self) -> bool:
        """Check if running in enhanced mode."""
        return self.system_complexity == "enhanced"
    
    @property
    def effective_checkpoint_times(self) -> List[str]:
        """Get checkpoint times based on complexity mode."""
        if self.is_simple_mode:
            # Simplified mode uses fewer checkpoints
            return ["10:30", "11:00", "12:30", "14:45"]
        else:
            # Standard/Enhanced modes use full schedule
            return self.checkpoint_times
    
    @property
    def effective_use_mock_data(self) -> bool:
        """Determine if mock data should be used based on mode."""
        if self.is_simple_mode:
            return True  # Simple mode defaults to mock data
        else:
            return self.use_mock_data
    
    @property
    def effective_enhanced_features(self) -> dict:
        """Get enhanced features status based on complexity mode."""
        if self.is_enhanced_mode:
            return {
                "enable_greeks": self.enable_greeks,
                "enable_advanced_gex": self.enable_advanced_gex,
                "enable_volume_analysis": self.enable_volume_analysis
            }
        else:
            # Simple/Standard modes disable enhanced features
            return {
                "enable_greeks": False,
                "enable_advanced_gex": False,
                "enable_volume_analysis": False
            }
    
    def get_scorer_mode(self) -> str:
        """Get the appropriate scorer mode based on system complexity."""
        return self.system_complexity
    
    class Config:
        env_file = ".env"
        env_prefix = "M8C_"  # Magic8-Companion prefix


# Global settings instance
settings = Settings()


# Backward compatibility function for simplified settings
def get_simplified_settings():
    """
    Backward compatibility function that returns settings configured for simple mode.
    This allows existing main_simplified.py to work without changes.
    """
    # Temporarily override complexity for simplified mode
    temp_settings = Settings(system_complexity="simple")
    return temp_settings
