# IBKR Integration Documentation

## Overview
The Magic8-Companion now supports Interactive Brokers (IBKR) as the primary data source for all market data components. This provides significant advantages over Yahoo Finance, including real-time data, accurate Greeks calculations, and better data quality.

## Key Benefits of IBKR Integration

### Real-Time Data
- **No Delays**: IBKR provides real-time market data vs Yahoo's 15-minute delay
- **Live Greeks**: Accurate Greeks calculated by the exchange
- **Current Prices**: Real-time bid/ask spreads and last traded prices

### Superior Data Quality
- **Exchange-Calculated Greeks**: Delta, Gamma, Theta, Vega directly from CBOE/exchanges
- **Accurate Implied Volatility**: Real-time IV from market makers
- **Complete Option Chain**: All strikes with current market data
- **Better Volume/OI Data**: More accurate open interest and volume figures

### Production-Ready Features
- **Automatic Fallback**: Falls back to Yahoo Finance if IBKR connection fails
- **Connection Management**: Automatic connection handling with context managers
- **Error Recovery**: Robust error handling and logging

## Prerequisites

### 1. IBKR Account Requirements
- Active IBKR account with appropriate market data subscriptions
- API access enabled in your account
- Market data subscriptions for options you want to trade (OPRA, CBOE, etc.)

### 2. Software Requirements
- TWS (Trader Workstation) or IB Gateway installed
- Python 3.8+ with `ib_async` library
- Network access to TWS/Gateway (typically localhost)

### 3. TWS/Gateway Configuration
1. Open TWS or IB Gateway
2. Go to File → Global Configuration → API → Settings
3. Enable these settings:
   - ✓ Enable ActiveX and Socket Clients
   - ✓ Download open orders on connection
   - Socket port: 7497 (paper) or 7496 (live)
   - ✓ Allow connections from localhost only (recommended)
   - Master API client ID: Leave blank
4. Add trusted IP: 127.0.0.1

## Installation

The IBKR integration uses `ib_async` which is already in requirements.txt:
```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables
Add these to your `.env` file:

```bash
# Enable IBKR as primary data source
USE_IBKR_DATA=true

# IBKR Connection Settings
IBKR_HOST=127.0.0.1      # TWS/Gateway host
IBKR_PORT=7497           # 7497 for paper, 7496 for live
IBKR_CLIENT_ID=1         # Unique client ID

# Fallback Settings
IBKR_FALLBACK_TO_YAHOO=true  # Use Yahoo if IBKR fails
```

### Connection Ports
- **Paper Trading**: Port 7497
- **Live Trading**: Port 7496
- Ensure your firewall allows connections to these ports

## Usage

### Basic Testing
Test IBKR connection and data retrieval:
```bash
# Test connection
python scripts/test_ibkr_market_data.py

# Test specific symbols
python scripts/test_ibkr_market_data.py SPY QQQ IWM

# Compare with Yahoo data
python scripts/test_ibkr_market_data.py SPY --compare
```

### Production Usage
The system automatically uses IBKR when `USE_IBKR_DATA=true`:
```bash
# Set environment variable
export USE_IBKR_DATA=true

# Run normal tests
python scripts/test_enhanced_indicators.py
```

## Data Flow

### 1. Market Data Request
```
Magic8-Companion → MarketAnalyzer → IBKRMarketData → TWS/Gateway → Exchange
```

### 2. Data Components Retrieved
- **Underlying Price**: Real-time last/bid/ask
- **Option Chain**: All strikes within 5% of spot
- **Greeks**: Delta, Gamma, Theta, Vega for each strike
- **Market Data**: Volume, Open Interest, Bid/Ask spreads
- **Implied Volatility**: Exchange-calculated IV

### 3. Fallback Mechanism
```
IBKR Connection Failed → Log Warning → Fallback to Yahoo → Continue Operation
```

## Implementation Details

### Key Classes

#### IBKRMarketData
Main class for IBKR data retrieval:
- Manages TWS connection
- Fetches option chains with Greeks
- Handles contract specifications
- Implements fallback logic

#### IBKRConnection
Context manager for connection handling:
- Automatic connection on entry
- Automatic disconnection on exit
- Exception handling

### Data Format
IBKR data is formatted to match existing interfaces:
```python
{
    "symbol": "SPY",
    "spot_price": 435.50,
    "iv_percentile": 45.0,
    "expected_range_pct": 0.0085,
    "gamma_environment": "Range-bound, moderate gamma",
    "option_chain": [
        {
            "strike": 435.0,
            "implied_volatility": 0.1850,
            "call_gamma": 0.0234,
            "put_gamma": 0.0221,
            "call_delta": 0.5123,
            "put_delta": -0.4877,
            # ... more Greeks and market data
        }
    ],
    "data_source": "IBKR"
}
```

## Troubleshooting

### Connection Issues
1. **"Failed to connect to IBKR"**
   - Ensure TWS/Gateway is running
   - Check port settings match configuration
   - Verify API settings are enabled

2. **"No market data permissions"**
   - Check IBKR market data subscriptions
   - Ensure account has options trading permissions
   - Verify symbol is available on your subscribed exchanges

3. **"Greeks not populated"**
   - Some contracts may need subscription to OPRA
   - Check if market is open
   - Verify contract specifications

### Data Issues
1. **Missing strikes**
   - IBKR only shows liquid strikes
   - Adjust strike range parameters if needed

2. **Zero Greeks values**
   - May indicate market is closed
   - Check if contract is properly qualified
   - Ensure market data subscription includes Greeks

### Performance Optimization
1. **Reduce API calls**
   - Cache frequently used data
   - Batch requests when possible

2. **Connection management**
   - Keep connection alive for multiple requests
   - Use connection pooling for high-frequency updates

## Best Practices

### 1. Market Hours
- Best results during regular trading hours (9:30 AM - 4:00 PM ET)
- Greeks may be stale outside market hours
- Consider using snapshot data for after-hours

### 2. Symbol Selection
- Use liquid symbols for best data quality
- Index options (SPX) have most reliable Greeks
- ETF options (SPY, QQQ, IWM) have good liquidity

### 3. Error Handling
- Always check for None returns
- Log all errors for debugging
- Implement retry logic for transient failures

### 4. Production Deployment
- Use dedicated IB Gateway for stability
- Monitor connection status
- Set up alerts for connection failures
- Consider redundant data sources

## API Rate Limits
IBKR has various rate limits:
- Max 50 messages per second
- Snapshot data doesn't count against limits
- Consider using snapshot mode for scanning

## Migration from Yahoo

### Code Changes
No code changes required! The system automatically uses IBKR when enabled:
```python
# This works with both Yahoo and IBKR
analyzer = MarketAnalyzer()
data = await analyzer.analyze_symbol("SPY")
```

### Data Differences
- IBKR Greeks are more accurate
- Real-time vs 15-minute delayed
- More complete option chain data
- Better handling of 0DTE options

## Security Considerations

### Connection Security
- Use localhost connections only
- Don't expose TWS ports to internet
- Use unique client IDs per application

### API Credentials
- Never commit IBKR credentials to git
- Use environment variables for configuration
- Rotate client IDs periodically

## Support and Resources

### IBKR Documentation
- [TWS API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib_async Documentation](https://ib-async.readthedocs.io/)
- [IBKR Market Data Subscriptions](https://www.interactivebrokers.com/en/trading/marketdata/research-subscriptions.php)

### Debugging
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues
See [IBKR API FAQ](https://www.interactivebrokers.com/en/software/api/apiguide/tables/api_message_codes.htm) for error codes.

## Conclusion
The IBKR integration provides production-grade market data for the Magic8-Companion system. With real-time data and accurate Greeks, the system can make more informed trading recommendations. The automatic fallback to Yahoo ensures reliability even if IBKR connection issues occur.
