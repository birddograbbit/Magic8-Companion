# IBKR Connection Troubleshooting Guide

This guide addresses common issues with Interactive Brokers (IBKR) connection and option contract qualification, especially for 0DTE (zero days to expiration) trading.

## Recent Fixes (June 17, 2025)

### Important: Correct File Location
The IBKR connection logic is in **`ib_client.py`**, not `ibkr_market_data.py`. Make sure to apply fixes to the correct file!

### 1. Enhanced Symbol Support
The system now automatically tries multiple symbol variations:
- **SPX**: Tries both `SPXW` and `SPX` symbols (prefers SPXW for 0DTE)
- **SPXW** is preferred for 0DTE options on S&P 500

### 2. Multiple Exchange Fallback
The system now tries multiple exchanges in order of preference:
- All symbols prioritize `SMART` routing for better fills
- Fallback exchanges are configured per symbol:
  - **SPX/SPXW**: SMART → CBOE
  - **RUT**: SMART → CBOE → RUSSELL
  - **SPY**: SMART → CBOE → ARCA → BATS → AMEX → ISE
  - **QQQ**: SMART → NASDAQ → CBOE → ARCA
  - **IWM**: SMART → ARCA → CBOE

### 3. Improved Contract Qualification
- Underlying contracts now use fallback logic
- Option contracts automatically try multiple exchanges
- Better handling of 0DTE expirations
- Enhanced logging for debugging

## Common Issues and Solutions

### Issue: "No security definition has been found"
This error occurs when IBKR cannot find the requested contract.

**Solutions:**
1. The system will now automatically try alternative symbols (SPX → SPXW)
2. Multiple exchanges are attempted automatically
3. If still failing, check:
   - Market hours (options may not be available pre-market)
   - Expiration date validity
   - IBKR subscription level (some data requires additional subscriptions)

### Issue: SPX 0DTE Options Not Found
SPX 0DTE options are often listed under SPXW (weekly options).

**Solution:** The system now automatically checks both SPX and SPXW symbols.

### Issue: Wrong Exchange for Index Options
Different indices trade on different exchanges.

**Solution:** The system now uses SMART routing by default, which automatically finds the best exchange.

### Issue: Rate Limiting from Yahoo Finance
When IBKR fails, the system falls back to Yahoo Finance, which has rate limits.

**Solutions:**
1. Fix IBKR connection to avoid fallback
2. Add delays between requests
3. Use cache data when available

## Architecture Overview

### Data Flow
```
1. Magic8-Companion → market_analysis.py → ib_client.py → IBKR
2. If successful: Writes real data + option chain to cache
3. MLOptionTrading → reads cache → uses option chain data

If IBKR fails:
1. Falls back to Yahoo Finance → limited data
2. Falls back to mock data → no option chain
3. MLOptionTrading can't find option chain → uses its own fallback
```

### Key Files
- **`magic8_companion/modules/ib_client.py`** - Main IBKR connection logic (THIS IS THE FILE TO FIX!)
- **`magic8_companion/modules/market_analysis.py`** - Calls ib_client and manages fallbacks
- **`magic8_companion/modules/ibkr_market_data.py`** - Alternative implementation (NOT USED BY DEFAULT)

## Configuration

### Environment Variables
```bash
# IBKR Connection Settings
IBKR_HOST=127.0.0.1
IBKR_PORT=7497  # TWS Paper Trading
# IBKR_PORT=7496  # TWS Live Trading
# IBKR_PORT=4002  # IB Gateway Paper
# IBKR_PORT=4001  # IB Gateway Live
IBKR_CLIENT_ID=1
MARKET_DATA_PROVIDER=ib

# Fallback Settings
IBKR_FALLBACK_TO_YAHOO=true
```

### TWS/IB Gateway Configuration
1. Enable API connections in TWS/Gateway
2. Configure trusted IP addresses (add 127.0.0.1)
3. Ensure "Download open orders on connection" is checked
4. Set appropriate socket port (see above)

## Testing Your Connection

Run the test script to verify IBKR connectivity:

```bash
cd ~/magic8/Magic8-Companion
python -m magic8_companion.modules.ib_client
```

Expected output:
```
Connecting to IB: 127.0.0.1:7497 with ClientID: 1
Successfully connected to IB.

Fetching ATM options for SPX (0DTE)...
Qualified SPX as SPXW on SMART
SPX Option: K=6000 C, Bid=45.20, Ask=45.50, IV=0.1523
SPX Option: K=6000 P, Bid=43.10, Ask=43.40, IV=0.1498
...
```

## Success Confirmation

When working correctly, you should see:

### In Magic8-Companion logs:
```
- "Qualified SPX as SPXW on SMART" (or similar)
- NO "No security definition found" errors
- NO "Falling back to mock data" messages
- Option chain data being written to cache
```

### In MLOptionTrading logs:
```
- "Using cached IBKR data for SPX"
- "Found cached option chain with X strikes"
- Net GEX calculations using real data
- NO "No cached option chain" warnings
```

## Advanced Debugging

### Enable Detailed Logging
```python
import logging
logging.getLogger('magic8_companion.modules.ib_client').setLevel(logging.DEBUG)
logging.getLogger('magic8_companion.modules.market_analysis').setLevel(logging.DEBUG)
```

### Common Log Messages
- `"Qualified SPX as SPXW on SMART"` - Successfully found alternative symbol
- `"Using SMART routing for better fills"` - Exchange routing optimization
- `"Found 0DTE expiration"` - Successfully identified today's options
- `"No chains found for SPX, trying SPXW"` - Automatic symbol fallback

### Verify Cache Contents
Check if option chain is being cached:
```bash
cat data/market_data_cache.json | jq '.data.SPX.option_chain | length'
```
Should return a number > 0 if option chain is cached.

## Performance Optimization

### Strike Limits
To avoid IBKR ticker limits:
- Maximum 25 strikes above ATM
- Maximum 25 strikes below ATM
- Process options in batches of 20

### Connection Management
- Use context managers for automatic cleanup
- Reuse connections when possible
- Implement proper disconnect handling

## Troubleshooting Checklist

1. ✓ TWS/Gateway is running and API is enabled
2. ✓ Correct port is configured (7497 for paper trading)
3. ✓ Market is open (regular trading hours)
4. ✓ Valid market data subscriptions in IBKR
5. ✓ Firewall allows connections on configured port
6. ✓ No other applications using the same client ID
7. ✓ Using correct file: `ib_client.py` (not `ibkr_market_data.py`)

## Support

For additional help:
1. Check IBKR API documentation
2. Review logs in `magic8_companion/modules/ib_client.py`
3. Test with different symbols to isolate issues
4. Verify market data subscriptions in IBKR account
