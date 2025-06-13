"""
Legacy combo_scorer_simplified.py - DEPRECATED
This file now proxies to unified_combo_scorer.py in simple mode for backward compatibility.

MIGRATION PATH:
- Change imports from: from .combo_scorer_simplified import ComboScorer
- Change imports to:   from .unified_combo_scorer import create_scorer
                      scorer = create_scorer("simple")
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "combo_scorer_simplified.py is deprecated. Use unified_combo_scorer.create_scorer('simple') instead. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to the unified scorer in simple mode
from .unified_combo_scorer import create_scorer

# Create simple mode scorer for backward compatibility
class ComboScorer:
    """Backward compatibility wrapper for simple mode scorer."""
    def __init__(self):
        self._scorer = create_scorer("simple")
    
    def score_combo_types(self, market_data, symbol):
        return self._scorer.score_combo_types(market_data, symbol)

# Maintain backward compatibility
__all__ = ['ComboScorer']
