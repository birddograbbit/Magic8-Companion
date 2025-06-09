"""
Simplified market analyzer for Magic8-Companion.
Provides basic market analysis without requiring live data feeds.
"""
import logging
from typing import Dict, Optional
from ..config_simplified import settings

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Simplified market analyzer using mock data or basic calculations."""
    
    def __init__(self):
        self.use_mock_data = settings.use_mock_data
        
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol."""
        logger.debug(f"Analyzing market conditions for {symbol}")
        
        if self.use_mock_data:
            return self._get_mock_market_data(symbol)
        else:
            # TODO: Implement real market data analysis
            logger.warning("Real market data analysis not implemented yet, using mock data")
            return self._get_mock_market_data(symbol)
    
    def _get_mock_market_data(self, symbol: str) -> Dict:
        """Generate mock market data for testing."""
        # Simulate different market conditions based on symbol
        if symbol == "SPX":
            base_iv = 65.0
            base_range = 0.008
        elif symbol == "SPY":
            base_iv = 62.0
            base_range = 0.007
        elif symbol == "QQQ":
            base_iv = 70.0
            base_range = 0.012
        elif symbol == "RUT":
            base_iv = 75.0
            base_range = 0.015
        else:
            base_iv = settings.mock_iv_percentile
            base_range = settings.mock_expected_range_pct
        
        # Simulate time-based variations
        from datetime import datetime
        hour = datetime.now().hour
        
        # Make conditions more volatile in afternoon
        time_multiplier = 1.0 + (hour - 12) * 0.1 if hour > 12 else 1.0
        
        return {
            "symbol": symbol,
            "iv_percentile": base_iv * time_multiplier,
            "expected_range_pct": base_range * time_multiplier,
            "gamma_environment": self._determine_gamma_environment(base_iv, base_range),
            "analysis_timestamp": datetime.now().isoformat(),
            "is_mock_data": True
        }
    
    def _determine_gamma_environment(self, iv_percentile: float, range_pct: float) -> str:
        """Determine gamma environment description."""
        if iv_percentile < 30 and range_pct < 0.005:
            return "Low volatility, high gamma"
        elif iv_percentile > 70 and range_pct > 0.015:
            return "High volatility, low gamma"
        elif range_pct < 0.008:
            return "Range-bound, moderate gamma"
        else:
            return "Directional, variable gamma"
