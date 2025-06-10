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

---

# Fix Applied: py_vollib_vectorized API Error

## Issue
When running the test script, encountered:
```
ERROR - Error calculating Greeks: module 'py_vollib_vectorized' has no attribute 'black_scholes'
```

## Root Cause
The greeks_wrapper.py was using an incorrect API path for py_vollib_vectorized. The code was trying to access `vol.black_scholes.greeks.analytical` which doesn't exist in the vectorized library.

## Solution Applied
Changed the import and usage to the correct API:
- Import: `from py_vollib_vectorized import get_all_greeks`
- Usage: Direct call to `get_all_greeks()` function with proper parameters

## Key Changes in greeks_wrapper.py
- Updated `_calculate_vectorized` method to use the correct `get_all_greeks()` function
- Added proper parameters: flag, S, K, t, r, sigma, model='black_scholes', return_as='dict'
- Ensured all returned values are numpy arrays for consistency

---

# Fix Applied: datetime.utcnow() Deprecation Warning

## Issue
Python 3.13 deprecation warning:
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version
```

## Solution Applied
- Updated import: `from datetime import datetime, timezone`
- Changed: `datetime.utcnow().isoformat() + "Z"`
- To: `datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')`

This ensures timezone-aware datetime objects are used, which is the recommended approach for UTC timestamps.

---

## Testing After Fixes
After applying all fixes, the test script should run successfully:
```bash
cd /Users/jt/magic8/Magic8-Companion
git pull origin dev-enhanced-indicators
python scripts/test_enhanced_indicators.py
```

Expected output:
- No errors or warnings
- Successful scoring for all three strategies (Butterfly, Iron_Condor, Vertical)
- Enhanced scores showing adjustments from Greeks, GEX, and Volume/OI analysis
- Comparison between enhanced and basic scoring modes
- Test results saved to JSON file
