"""
Simplified market analyzer for Magic8-Companion.
Provides basic market analysis without requiring live data feeds.
"""
import logging
from typing import Dict, Optional
from ..config_simplified import settings
import random

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
        """Generate mock market data for testing with more realistic variations."""
        from datetime import datetime
        
        # Create time-based seed for consistent results within same minute
        current_minute = datetime.now().strftime("%Y%m%d%H%M")
        random.seed(f"{symbol}_{current_minute}")
        
        # Generate market scenarios with more realistic distributions
        scenario = random.choice([
            # Low volatility scenarios (good for butterflies)
            {"iv": 25.0, "range": 0.004, "env": "Low volatility, high gamma"},
            {"iv": 35.0, "range": 0.005, "env": "Low volatility, pinning conditions"},
            # Moderate volatility (good for iron condors)
            {"iv": 45.0, "range": 0.008, "env": "Range-bound, moderate gamma"},
            {"iv": 55.0, "range": 0.010, "env": "Range-bound, neutral conditions"},
            # High volatility (good for verticals)
            {"iv": 65.0, "range": 0.012, "env": "Directional, variable gamma"},
            {"iv": 75.0, "range": 0.015, "env": "High volatility, directional"},
            {"iv": 85.0, "range": 0.018, "env": "High volatility, low gamma"}
        ])
        
        # Add symbol-specific adjustments
        if symbol == "SPX":
            # SPX tends to have slightly lower volatility
            scenario["iv"] *= 0.9
            scenario["range"] *= 0.9
        elif symbol == "QQQ":
            # Tech-heavy QQQ tends to be more volatile
            scenario["iv"] *= 1.1
            scenario["range"] *= 1.1
        elif symbol == "RUT":
            # Small caps are typically most volatile
            scenario["iv"] *= 1.2
            scenario["range"] *= 1.2
        
        # Add some random noise (±10%)
        scenario["iv"] *= random.uniform(0.9, 1.1)
        scenario["range"] *= random.uniform(0.9, 1.1)
        
        return {
            "symbol": symbol,
            "iv_percentile": round(scenario["iv"], 1),
            "expected_range_pct": round(scenario["range"], 4),
            "gamma_environment": scenario["env"],
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
