"""
Legacy combo_scorer.py - DEPRECATED
This file now proxies to unified_combo_scorer.py for backward compatibility.

MIGRATION PATH:
- Change imports from: from .combo_scorer import ComboScorer
- Change imports to:   from .unified_combo_scorer import ComboScorer
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "combo_scorer.py is deprecated. Please use unified_combo_scorer.py instead. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to the unified scorer in standard mode
from .unified_combo_scorer import ComboScorer, generate_recommendation

# Maintain backward compatibility
__all__ = ['ComboScorer', 'generate_recommendation']
