# IBKR Strike Limits and Error Handling Fix

## Problem Analysis

Based on the error logs, several issues were identified:

1. **"No security definition has been found"** - Some strikes (6195, 6205) don't exist in the chain
2. **"Max number of tickers has been reached"** (Error 101) - Hitting IBKR's concurrent ticker limit (~100)
3. **"Can't find EId with tickerId"** - Subscription management errors
4. **SPX vs SPXW confusion** - Not using the correct trading class for 0DTE

## Root Causes

1. **Too many concurrent requests**: 121 strikes × 2 (call/put) = 242 contracts exceeded IBKR's limits
2. **Invalid strikes**: Some strikes in the chain don't have valid contracts
3. **Trading class mismatch**: SPX monthly options vs SPXW weekly options for 0DTE
4. **Poor error recovery**: Failed subscriptions weren't cleaned up properly

## Solution Overview

### 1. Strike Limits
- Limited to maximum 25 strikes above ATM and 25 below ATM
- Total maximum of 51 strikes (including ATM)
- This keeps us well under IBKR's ticker limits

### 2. Trading Class Filtering
- For SPX, prefer SPXW trading class (weekly/daily options for 0DTE)
- SPX = monthly options (AM-settled)
- SPXW = weekly/daily options (PM-settled) - better for 0DTE

### 3. Batch Processing
- Process options in batches of 20 contracts
- Separate batches for OI streaming and snapshot data
- Prevents hitting concurrent ticker limits

### 4. Enhanced Error Handling
- Better contract qualification with individual try/catch
- Proper cleanup of all market data subscriptions
- Continue processing even if some contracts fail

## Implementation Details

### Key Constants
```python
MAX_STRIKES_ABOVE_ATM = 25  # Maximum strikes above ATM
MAX_STRIKES_BELOW_ATM = 25  # Maximum strikes below ATM
MAX_CONCURRENT_TICKERS = 90  # Stay well below IBKR's limit
BATCH_SIZE = 20  # Process options in batches
```

### Trading Class Map
```python
trading_class_map = {
    'SPX': 'SPXW',  # Use weekly options for 0DTE
    'RUT': 'RUT',
    'QQQ': 'QQQ',
    'IWM': 'IWM',
    'SPY': 'SPY'
}
```

### Strike Selection Algorithm
1. Find ATM strike
2. Select up to 25 strikes below ATM
3. Include ATM strike
4. Select up to 25 strikes above ATM
5. Total: maximum 51 strikes

### Batch Processing Flow
1. Qualify all contracts first
2. Get OI data via streaming in batches of 20
3. Get snapshot data (prices/Greeks) in batches of 20
4. Properly cancel all subscriptions after each batch

## Benefits

1. **No more ticker limit errors** - Stay well under IBKR's limits
2. **Faster processing** - Fewer contracts to process
3. **Better reliability** - Robust error handling
4. **Correct options for 0DTE** - Use SPXW for intraday trading
5. **Cleaner resource management** - Proper subscription cleanup

## Testing

Run the test script to verify:
```bash
python scripts/test_strike_limits.py
```

Expected results:
- Maximum 51 strikes retrieved
- No "Max tickers" errors
- Successful OI and Greeks data
- Proper SPXW trading class for SPX

## Comparison with Production Systems

Based on research into production 0DTE trading systems:
- **jensolson/SPX-Gamma-Exposure** - Handles both SPX and SPXW
- **aicheung/0dte-trader** - Specifically designed for 0DTE with IBKR
- **GEX calculations** - Use limited strikes around ATM for efficiency

Our implementation follows these best practices while adding robust error handling.
