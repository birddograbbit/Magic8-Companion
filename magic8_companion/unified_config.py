"""
Unified configuration for Magic8-Companion recommendation engine.
Consolidates config.py and config_simplified.py into one flexible system.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from typing import List, Union, Optional, Any, Dict
from enum import Enum
import json


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
    supported_symbols: Union[str, List[str]] = ["SPX"] # ["SPX", "SPY", "QQQ", "RUT"]
    checkpoint_times: Union[str, List[str]] = ["10:00", "10:10", "10:20", "10:30", "10:40", "10:50", "11:00", "11:10", "11:20", "11:30", "11:40", "11:50", "12:00", "12:10", "12:20", "12:30", "12:40", "12:50", "13:00", "13:10", "13:20", "13:30", "13:40", "13:50", "14:00", "14:10", "14:20", "14:30", "14:40", "14:50"]
    
    # Scoring thresholds - MADE MORE LENIENT
    min_recommendation_score: int = 60  # Down from 70
    min_score_gap: int = 10  # Down from 15

    # === ML INTEGRATION SETTINGS ===
    enable_ml_integration: bool = Field(False, env='M8C_ENABLE_ML_INTEGRATION')
    ml_weight: float = Field(0.35, env='M8C_ML_WEIGHT')
    ml_path: str = Field('../MLOptionTrading', env='M8C_ML_PATH')
    enable_ml_5min: bool = Field(False, env='M8C_ENABLE_ML_5MIN')
    ml_5min_interval: int = Field(5, env='M8C_ML_5MIN_INTERVAL')
    ml_5min_confidence_threshold: float = Field(0.65, env='M8C_ML_5MIN_CONFIDENCE_THRESHOLD')
    ml_5min_merge_strategy: str = Field('overlay', env='M8C_ML_5MIN_MERGE_STRATEGY')
    
    # === MARKET DATA SETTINGS ===
    
    # Market analysis settings (simplified mode uses mock data)
    use_mock_data: bool = False  # Set to true for testing
    mock_iv_percentile: float = 65.0
    mock_expected_range_pct: float = 0.008  # 0.8%
    
    # Live data provider selection
    market_data_provider: str = "ib"  # yahoo, ib, or polygon
    data_provider: str = "ib"  # For gamma analysis: ib, yahoo, polygon
    
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
    
    # OI Streaming settings
    enable_oi_streaming: bool = True  # Enable/disable OI streaming
    oi_streaming_timeout: float = 2.0  # Timeout for OI data collection
    
    # === API KEYS ===
    
    polygon_api_key: str = ""
    
    # === ENHANCED INDICATORS (only used in enhanced mode) ===
    
    enable_greeks: bool = False
    enable_advanced_gex: bool = False
    enable_volume_analysis: bool = False
    
    # === GAMMA INTEGRATION SETTINGS ===
    
    enable_enhanced_gex: bool = True  # Enable integrated enhanced gamma analysis
    # DEPRECATED: The following are no longer used as gamma is integrated
    # ml_option_trading_path: str = "../MLOptionTrading"
    # gamma_integration_mode: str = "file"
    gamma_max_age_minutes: int = 5  # Max age for gamma data before refresh
    
    # === NATIVE GAMMA SETTINGS ===
    
    # Gamma analysis symbols
    gamma_symbols: Union[str, List[str]] = ["SPX"]
    
    # Gamma scheduler settings
    gamma_scheduler_mode: str = "scheduled"  # scheduled or interval
    gamma_scheduler_times: Union[str, List[str]] = ["10:00", "10:10", "10:20", "10:30", "10:40", "10:50", "11:00", "11:10", "11:20", "11:30", "11:40", "11:50", "12:00", "12:10", "12:20", "12:30", "12:40", "12:50", "13:00", "13:10", "13:20", "13:30", "13:40", "13:50", "14:00", "14:10", "14:20", "14:30", "14:40", "14:50"]
    gamma_scheduler_interval: int = 5  # minutes for interval mode
    
    # Gamma calculation settings - Use string format in .env
    gamma_spot_multipliers: Union[str, Dict[str, int]] = {"SPX": 10, "RUT": 10, "DEFAULT": 100}
    gamma_regime_thresholds: Union[str, Dict[str, float]] = {
        "extreme": 5e9,    # $5B
        "high": 1e9,       # $1B
        "moderate": 500e6  # $500M
    }
    
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
    iron_condor_iv_range: Union[str, List[int]] = [25, 85]  # Expanded from [30, 80]
    vertical_min_iv: int = 40  # Down from 50
    
    # === FIELD VALIDATORS ===
    
    @field_validator('supported_symbols', 'checkpoint_times', 'gamma_symbols', 'gamma_scheduler_times', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated strings or JSON arrays into lists."""
        if isinstance(v, str):
            # Handle empty strings
            if not v.strip():
                return []
            
            # Try to parse as JSON array first (for backward compatibility)
            v_stripped = v.strip()
            if v_stripped.startswith('[') and v_stripped.endswith(']'):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, fall back to comma-separated
                    pass
            
            # Fall back to comma-separated parsing
            return [item.strip() for item in v.split(',') if item.strip()]
        return v
    
    @field_validator('iron_condor_iv_range', mode='before')
    @classmethod
    def parse_int_list_fields(cls, v: Union[str, List[int]]) -> List[int]:
        """Parse comma-separated strings or JSON arrays into list of integers."""
        if isinstance(v, str):
            # Handle empty strings
            if not v.strip():
                return []
            
            # Try to parse as JSON array first (for backward compatibility)
            v_stripped = v.strip()
            if v_stripped.startswith('[') and v_stripped.endswith(']'):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [int(item) for item in parsed]
                except (json.JSONDecodeError, ValueError, TypeError):
                    # If JSON parsing fails, fall back to comma-separated
                    pass
            
            # Fall back to comma-separated parsing
            return [int(item.strip()) for item in v.split(',') if item.strip()]
        return v
    
    @field_validator('gamma_spot_multipliers', 'gamma_regime_thresholds', mode='before')
    @classmethod
    def parse_dict_fields(cls, v: Union[str, Dict]) -> Dict:
        """Parse JSON strings into dictionaries."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped:
                try:
                    return json.loads(v_stripped)
                except (json.JSONDecodeError, ValueError):
                    # Return default values if parsing fails
                    if 'multipliers' in cls.__name__:
                        return {"SPX": 10, "RUT": 10, "DEFAULT": 100}
                    else:
                        return {
                            "extreme": 5e9,
                            "high": 1e9,
                            "moderate": 500e6
                        }
            # Return default values for empty strings
            if 'multipliers' in cls.__name__:
                return {"SPX": 10, "RUT": 10, "DEFAULT": 100}
            else:
                return {
                    "extreme": 5e9,
                    "high": 1e9,
                    "moderate": 500e6
                }
        return v
    
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
            return self.checkpoint_times if isinstance(self.checkpoint_times, list) else self.checkpoint_times
    
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
    
    def get_gamma_spot_multiplier(self, symbol: str) -> int:
        """Get the spot multiplier for a given symbol."""
        multipliers = self.gamma_spot_multipliers
        if isinstance(multipliers, dict):
            return multipliers.get(symbol, multipliers.get("DEFAULT", 100))
        return 100
    
    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="M8C_",
        # This is important: tell pydantic_settings not to parse complex fields as JSON
        json_schema_extra={
            "env_parse_none_str": "null",
            "env_nested_delimiter": "__"
        }
    )


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
