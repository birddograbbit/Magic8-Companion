# NaN Volume Conversion Fix

## Issue Description
When fetching option data from Interactive Brokers, the ticker volume field sometimes returns NaN (Not a Number) values, especially:
- Outside regular trading hours
- For options with no trading activity
- During data feed interruptions

This caused the error: `cannot convert float NaN to integer`

## Root Cause
The code was attempting to convert volume data directly to integers without checking for NaN values:
```python
strike_data['call_volume'] = int(ticker.volume or 0)
```

The `or 0` fallback doesn't work for NaN because:
- NaN is truthy in Python (not None or False)
- `float('nan') or 0` returns `nan`, not 0
- `int(nan)` raises ValueError

## Solution Applied
Added explicit NaN checking before integer conversion:
```python
# Handle NaN values in volume
volume = ticker.volume
if volume is not None and not math.isnan(volume):
    strike_data['call_volume'] = int(volume)
else:
    strike_data['call_volume'] = 0
```

This fix was applied to both call and put volume fields in `ibkr_market_data.py`.

## Files Modified
- `magic8_companion/modules/ibkr_market_data.py` - Added NaN handling for volume conversion

## Test Command
```bash
# Test the fix
python scripts/test_nan_fix.py

# Or run the original test
python scripts/verify_spx_fix.py
```

## Additional Notes
- The OI streaming function already had proper NaN handling
- This is a common issue with IB API data, especially for less liquid options
- The fix is consistent with ib_insync best practices for handling market data

## Related Issues
- SPY half-dollar strikes (587.5, 592.5, etc.) not found on NASDAQOM exchange
  - This is a separate issue related to exchange selection
  - SPY options might need to use a different exchange for certain strikes
