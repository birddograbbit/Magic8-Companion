"""
Native GEX Analyzer for Magic8-Companion.
Unified analyzer that replaces the external MLOptionTrading dependency.
"""
from typing import Dict, Optional, List
import logging
from datetime import datetime

from ..analysis.gamma import (
    GammaExposureCalculator,
    GammaLevels,
    MarketRegimeAnalyzer
)
from ..unified_config import settings

logger = logging.getLogger(__name__)


class NativeGEXAnalyzer:
    """
    Native GEX analyzer for Magic8-Companion.
    Provides interface compatible with EnhancedGEXWrapper for easy migration.
    """
    
    def __init__(self):
        """Initialize native GEX components."""
        # SPX uses 10x multiplier, others use 100x
        self.calculators = {
            'SPX': GammaExposureCalculator(spot_multiplier=10),
            'RUT': GammaExposureCalculator(spot_multiplier=10),
            'DEFAULT': GammaExposureCalculator(spot_multiplier=100)
        }
        self.levels_analyzer = GammaLevels()
        self.regime_analyzer = MarketRegimeAnalyzer()
        
        # Cache for results
        self._cache = {}
        self._cache_timestamp = {}
        
        logger.info("Native GEX Analyzer initialized")
    
    def analyze(self, symbol: str, spot_price: float, 
                option_chain: List[Dict]) -> Dict:
        """
        Complete GEX analysis.
        
        Args:
            symbol: Trading symbol
            spot_price: Current spot price
            option_chain: Option chain data
            
        Returns:
            Dict with complete GEX analysis
        """
        # Check cache first
        cache_key = f"{symbol}_{spot_price}"
        if self._is_cache_valid(cache_key):
            logger.debug(f"Using cached GEX for {symbol}")
            return self._cache[cache_key]
        
        # Select appropriate calculator
        calculator = self.calculators.get(
            symbol, 
            self.calculators['DEFAULT']
        )
        
        # Calculate GEX
        gex_data = calculator.calculate_gex(
            spot_price, 
            option_chain,
            use_0dte_multiplier=True,
            dte_multiplier=settings.gex_0dte_multiplier
        )
        
        # Find levels
        gex_data['levels'] = self.levels_analyzer.find_levels(
            gex_data['strike_gex'], 
            spot_price
        )
        
        # Analyze regime
        gex_data['regime_analysis'] = self.regime_analyzer.analyze_regime(
            gex_data, 
            spot_price
        )
        
        # Add symbol for reference
        gex_data['symbol'] = symbol
        
        # Cache results
        self._cache[cache_key] = gex_data
        self._cache_timestamp[cache_key] = datetime.now()
        
        return gex_data
    
    def calculate_gamma_exposure(self, symbol: str, market_data: Dict) -> Dict:
        """
        Calculate gamma exposure (compatible with EnhancedGEXWrapper interface).
        
        Args:
            symbol: Trading symbol
            market_data: Market data containing option chain
            
        Returns:
            Dict with GEX analysis results
        """
        try:
            # Extract required data
            option_chain = market_data.get('option_chain', [])
            spot_price = market_data.get('current_price', 0)
            
            if not option_chain or not spot_price:
                logger.warning(f"Insufficient data for GEX analysis of {symbol}")
                return self._empty_result(symbol)
            
            # Run analysis
            result = self.analyze(symbol, spot_price, option_chain)
            
            # Format for compatibility with existing code
            return self._format_result(result)
            
        except Exception as e:
            logger.error(f"GEX analysis failed for {symbol}: {e}", exc_info=True)
            return self._empty_result(symbol)
    
    def _format_result(self, gex_data: Dict) -> Dict:
        """Format results for compatibility with existing code."""
        regime_analysis = gex_data.get('regime_analysis', {})
        levels = gex_data.get('levels', {})
        
        return {
            'success': True,
            'symbol': gex_data.get('symbol'),
            'net_gex': gex_data.get('net_gex', 0),
            'net_gex_billions': gex_data.get('net_gex', 0) / 1e9,
            'regime': gex_data.get('regime', 'neutral'),
            'magnitude': regime_analysis.get('magnitude', 'low'),
            'bias': regime_analysis.get('bias', 'neutral'),
            'expected_behavior': regime_analysis.get('expected_behavior', {}),
            'levels': {
                'call_wall': levels.get('call_wall'),
                'put_wall': levels.get('put_wall'),
                'zero_gamma': levels.get('zero_gamma'),
                'high_gamma_strikes': levels.get('high_gamma_strikes', [])
            },
            'recommendations': regime_analysis.get('recommendations', []),
            'risk_metrics': regime_analysis.get('risk_metrics', {}),
            'timestamp': gex_data.get('timestamp', datetime.now().isoformat())
        }
    
    def _empty_result(self, symbol: str) -> Dict:
        """Return empty result structure."""
        return {
            'success': False,
            'symbol': symbol,
            'net_gex': 0,
            'net_gex_billions': 0,
            'regime': 'neutral',
            'magnitude': 'low',
            'bias': 'neutral',
            'expected_behavior': {},
            'levels': {
                'call_wall': None,
                'put_wall': None,
                'zero_gamma': None,
                'high_gamma_strikes': []
            },
            'recommendations': [],
            'risk_metrics': {},
            'timestamp': datetime.now().isoformat()
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache:
            return False
        
        # Check age
        timestamp = self._cache_timestamp.get(cache_key)
        if not timestamp:
            return False
        
        age_minutes = (datetime.now() - timestamp).total_seconds() / 60
        return age_minutes < settings.gamma_max_age_minutes
    
    def clear_cache(self):
        """Clear all cached results."""
        self._cache.clear()
        self._cache_timestamp.clear()
        logger.info("GEX cache cleared")
