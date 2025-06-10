# Fix Applied: AttributeError in EnhancedComboScorer

## Issue
When running `python scripts/test_enhanced_indicators.py`, encountered:
```
AttributeError: 'EnhancedComboScorer' object has no attribute 'strategy_weights'
```

## Root Cause
The `EnhancedComboScorer` class was trying to access `self.strategy_weights` in the `score_all_strategies` method, but this attribute was never defined in either the base `ComboScorer` class or the enhanced version.

## Solution Applied
1. Added `self.strategies = ["Butterfly", "Iron_Condor", "Vertical"]` to the `__init__` method
2. Refactored the class to properly override `score_combo_types` from the base class
3. Rewrote `score_all_strategies` to use the base class approach with enhanced scoring
4. Maintained backward compatibility while adding enhancement features

## Key Changes
- Override `score_combo_types` to add enhancements to base scores
- Simplified `score_all_strategies` to use the enhanced `score_combo_types` method
- Removed references to non-existent attributes
- Maintained the same output format for compatibility

## Testing
After this fix, the test script should run successfully. Run:
```bash
cd /Users/jt/magic8/Magic8-Companion
git pull origin dev-enhanced-indicators
python scripts/test_enhanced_indicators.py
```

The script should now show scoring results for all three strategies (Butterfly, Iron_Condor, Vertical) with optional enhancements applied based on environment variables.
