# Real Market Data Testing Guide

## Overview
The enhanced indicators system now supports real market data testing using Yahoo Finance (yfinance) as the data source. This allows you to test the scoring system with live option chain data, including all the fields needed for enhanced indicators.

## Prerequisites
- Market should be open for best results (Mon-Fri, 9:30 AM - 4:00 PM ET)
- Internet connection for fetching data from Yahoo Finance
- All dependencies installed (including yfinance)

## Quick Start

### 1. Basic Test
Test with default symbols (SPY, QQQ, IWM):
```bash
cd /Users/jt/magic8/Magic8-Companion
git pull origin dev-enhanced-indicators
python scripts/test_real_market_data.py
```

### 2. Test Specific Symbols
```bash
python scripts/test_real_market_data.py SPY AAPL TSLA
```

### 3. Check Market Hours First
```bash
python scripts/test_real_market_data.py --check-hours SPY
```

## What the Test Does

1. **Fetches Real Market Data**:
   - Current spot price
   - Option chain (nearest expiration)
   - Implied volatility for each strike
   - Open interest and volume
   - Calculates Greeks approximations

2. **Calculates Enhanced Indicators**:
   - Greeks adjustments (Delta, Gamma, Theta, Vega)
   - Advanced GEX (Gamma Exposure) analysis
   - Volume/OI sentiment analysis

3. **Scores Each Strategy**:
   - Butterfly (best for low IV, tight ranges)
   - Iron Condor (best for moderate IV, range-bound)
   - Vertical (best for high IV, directional moves)

4. **Provides Recommendations**:
   - Shows best strategy for current conditions
   - Displays confidence levels
   - Saves results with timestamp

## Understanding the Output

### Market Data Section
```
Market Data Retrieved:
  Data Source: Real (Yahoo Finance)
  Spot Price: $585.42
  IV Percentile: 45.0
  Expected Range: 1.25%
  Gamma Environment: Range-bound, moderate gamma
  Option Chain: 21 strikes loaded
```

### Strategy Scores Section
```
Strategy Scores:
  🥇 Iron_Condor:
     Score: 75.5 (HIGH)
     Trade: ✓ YES
  
  🥈 Butterfly:
     Score: 45.2 (MEDIUM)
     Trade: ✗ NO
```

### Data Quality Indicators
- **Real Data**: Successfully fetched from Yahoo Finance
- **Mock (Fallback)**: Real data unavailable, using mock data
- **No option chain**: Market closed or data unavailable

## Troubleshooting

### Common Issues

1. **"No option chain data available"**
   - Market may be closed
   - Symbol may not have options
   - Try liquid ETFs like SPY, QQQ

2. **"Failed to fetch data"**
   - Check internet connection
   - Symbol may be invalid
   - Yahoo Finance may be temporarily unavailable

3. **Stale Data on Weekends**
   - Option data from Friday's close
   - Volumes will be zero
   - Use for testing logic only

### Best Practices

1. **Test During Market Hours**:
   - Most accurate data
   - Real-time prices and volumes
   - Fresh Greeks calculations

2. **Use Liquid Symbols**:
   - SPY, QQQ, IWM for indices
   - AAPL, MSFT, TSLA for stocks
   - Avoid illiquid or newly listed symbols

3. **Compare Multiple Timeframes**:
   - Test at market open
   - Test mid-day
   - Test near close
   - Compare strategy recommendations

4. **Monitor Over Time**:
   - Run daily for a week
   - Track strategy performance
   - Adjust thresholds as needed

## Output Files

Results are saved with timestamps:
- `real_market_test_YYYYMMDD_HHMMSS.json`
- Contains all scores and market conditions
- Use for backtesting and analysis

## Environment Variables

Control the behavior with these settings:
```bash
# Enable/disable enhancements
export M8C_ENABLE_GREEKS=true
export M8C_ENABLE_ADVANCED_GEX=true
export M8C_ENABLE_VOLUME_ANALYSIS=true

# Force real data (no mock)
export M8C_USE_MOCK_DATA=false
```

## Next Steps

1. **Validation**:
   - Compare recommendations with your manual analysis
   - Verify Greeks calculations match your broker
   - Check if gamma environments align with market behavior

2. **Fine-tuning**:
   - Adjust score thresholds in wrapper modules
   - Modify strategy weights based on results
   - Add symbol-specific adjustments

3. **Integration**:
   - Connect to your broker API for execution
   - Set up automated monitoring
   - Create alerts for high-confidence trades

## Data Source Notes

**Yahoo Finance (yfinance)**:
- Free, no authentication required
- Good for testing and development
- May have delays or limitations
- Option chains updated every 15 minutes during market hours

For production use, consider:
- Interactive Brokers API (already in requirements)
- TD Ameritrade API
- Market data vendors

## Example Session

```bash
# Monday morning test
$ python scripts/test_real_market_data.py --check-hours SPY QQQ

Market Hours Check:
Current time (ET): 2024-03-25 10:30:00 EDT
✅ Market is OPEN
   Real-time data should be available

============================================================
Magic8-Companion Real Market Data Test
============================================================
Testing with symbols: SPY, QQQ
Data source: Yahoo Finance (yfinance)
============================================================

Analyzing SPY...
Market Data Retrieved:
  Data Source: Real (Yahoo Finance)
  Spot Price: $585.42
  IV Percentile: 35.0
  Expected Range: 0.85%
  Gamma Environment: Low volatility, high gamma
  
Strategy Scores:
  🥇 Butterfly:
     Score: 82.5 (HIGH)
     Trade: ✓ YES
...
```

Remember: Real market conditions are complex and dynamic. Always validate the system's recommendations with your own analysis and risk management rules.
