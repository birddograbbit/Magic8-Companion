"""
Fix for IBKR NaN open interest issue
This patch fixes the ValueError when converting NaN open interest to int
"""

import math

def safe_int_conversion(value, default=0):
    """
    Safely convert a value to int, handling NaN and None cases.
    
    Args:
        value: The value to convert (can be None, NaN, or numeric)
        default: Default value if conversion fails (default: 0)
    
    Returns:
        int: The converted integer value or default
    """
    # Handle None
    if value is None:
        return default
    
    # Handle NaN - check if value is NaN using math.isnan()
    try:
        if math.isnan(value):
            return default
    except (TypeError, ValueError):
        # If math.isnan() fails, it's not a float
        pass
    
    # Try to convert to int
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Example of the fix to apply in ibkr_market_data.py around line 290:
"""
# OLD CODE (causes ValueError with NaN):
call_oi = int(call_ticker.callOpenInterest or 0) if hasattr(call_ticker, 'callOpenInterest') else 0
put_oi = int(put_ticker.putOpenInterest or 0) if hasattr(put_ticker, 'putOpenInterest') else 0

# NEW CODE (handles NaN properly):
call_oi = safe_int_conversion(getattr(call_ticker, 'callOpenInterest', 0))
put_oi = safe_int_conversion(getattr(call_ticker, 'putOpenInterest', 0))

# OR inline without helper function:
call_oi = 0
if hasattr(call_ticker, 'callOpenInterest') and call_ticker.callOpenInterest is not None:
    try:
        # Check for NaN
        if not math.isnan(call_ticker.callOpenInterest):
            call_oi = int(call_ticker.callOpenInterest)
    except (TypeError, ValueError):
        pass

put_oi = 0
if hasattr(put_ticker, 'putOpenInterest') and put_ticker.putOpenInterest is not None:
    try:
        # Check for NaN
        if not math.isnan(put_ticker.putOpenInterest):
            put_oi = int(put_ticker.putOpenInterest)
    except (TypeError, ValueError):
        pass
"""
