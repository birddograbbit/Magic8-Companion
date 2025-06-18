"""
Legacy enhanced_combo_scorer.py - DEPRECATED
This file now proxies to unified_combo_scorer.py in enhanced mode for backward compatibility.

MIGRATION PATH:
- Change imports from: from .enhanced_combo_scorer import EnhancedComboScorer
- Change imports to:   from .unified_combo_scorer import create_scorer
                      scorer = create_scorer("enhanced")
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "enhanced_combo_scorer.py is deprecated. Use unified_combo_scorer.create_scorer('enhanced') instead. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to the unified scorer in enhanced mode
from .unified_combo_scorer import create_scorer

# Create enhanced mode scorer for backward compatibility  
class EnhancedComboScorer:
    """Backward compatibility wrapper for enhanced mode scorer."""
    def __init__(self):
        self._scorer = create_scorer("enhanced")
    
    async def score_combo_types(self, market_data, symbol):
        return await self._scorer.score_combo_types(market_data, symbol)
    
    async def score_all_strategies(self, market_data):
        """Legacy method for backward compatibility."""
        symbol = market_data.get('symbol', 'SPX')
        scores = await self._scorer.score_combo_types(market_data, symbol)
        
        # Convert to old format
        results = {}
        for strategy, score in scores.items():
            if score >= 65:
                confidence = "HIGH"
            elif score >= 45:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
                
            results[strategy] = {
                'score': score,
                'confidence': confidence,
                'should_trade': score >= 45,
                'enhanced': True
            }
        
        return results
    
    def get_enhancement_status(self):
        """Legacy method for backward compatibility."""
        return {
            'greeks_enabled': True,
            'advanced_gex_enabled': True,
            'volume_analysis_enabled': True
        }

# Maintain backward compatibility
__all__ = ['EnhancedComboScorer']
