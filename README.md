# Magic8-Companion

A simplified trade type recommendation engine that analyzes market conditions and outputs optimal strategy recommendations for the DiscordTrading system.

## 🚀 New: Enhanced Indicators (dev-enhanced-indicators branch)

This branch includes enhanced market indicators for improved prediction accuracy:
- **Greeks Analysis**: Delta, Theta, Vega calculations for better strategy selection
- **Advanced Gamma Exposure**: Net GEX, gamma walls, and 0DTE multipliers
- **Volume/OI Analytics**: Market sentiment and liquidity analysis

See [ENHANCED_INDICATORS.md](ENHANCED_INDICATORS.md) for details.

## Overview

Magic8-Companion is a lightweight companion service that:
- Analyzes market conditions at scheduled checkpoints (10:30, 11:00, 12:30, 14:45 ET)
- Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable
- Outputs recommendations to a JSON file for consumption by DiscordTrading
- Supports both mock data (for testing) and live market data via Yahoo Finance
- **NEW**: Optionally uses enhanced indicators for improved accuracy

## Architecture

```
Magic8 Discord → DiscordTrading → IB Execution
                     ↑
Magic8-Companion → recommendations.json
    ↑
Enhanced Indicators (Optional)
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/birddograbbit/Magic8-Companion.git
cd Magic8-Companion
git checkout dev-enhanced-indicators  # For enhanced features
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup Enhanced Indicators (Optional)

```bash
# Run setup script for enhanced dependencies
chmod +x scripts/setup_enhanced.sh
./scripts/setup_enhanced.sh

# Copy enhanced configuration
cp .env.enhanced .env
```

### 3. Configure

```bash
# Edit .env with your settings
nano .env
```

Key configuration options:
- `M8C_USE_MOCK_DATA`: Set to `true` for testing, `false` for live data
- `M8C_MARKET_DATA_PROVIDER`: Choose `yahoo`, `ib`, or `polygon`
- `M8C_SUPPORTED_SYMBOLS`: List of symbols to analyze
- `M8C_CHECKPOINT_TIMES`: Times to run analysis

Enhanced indicator options:
- `M8C_ENABLE_GREEKS`: Enable Greeks calculations (Delta, Theta, Vega)
- `M8C_ENABLE_ADVANCED_GEX`: Enable advanced Gamma Exposure analysis
- `M8C_ENABLE_VOLUME_ANALYSIS`: Enable Volume/OI sentiment analysis

### 4. Test

**Test basic functionality:**
```bash
python test_simplified.py
```

**Test enhanced indicators:**
```bash
python scripts/test_enhanced_indicators.py
```

**Test with live market data:**
```bash
# Edit .env and set M8C_USE_MOCK_DATA=false
python test_live_data.py
```

### 5. Run

```bash
python -m magic8_companion
```

## Output Format

The system outputs recommendations to `data/recommendations.json`:

```json
{
  "timestamp": "2025-06-09T15:30:00Z",
  "checkpoint_time": "10:30 ET",
  "enhanced_indicators": true,
  "recommendations": {
    "SPX": {
      "strategies": {
        "Butterfly": {
          "score": 85.0,
          "confidence": "HIGH",
          "should_trade": true,
          "rationale": "Low volatility environment (IV: 25%) with tight expected range (0.5%)"
        },
        "Iron_Condor": {
          "score": 65.0,
          "confidence": "MEDIUM",
          "should_trade": false
        },
        "Vertical": {
          "score": 50.0,
          "confidence": "LOW",
          "should_trade": false
        }
      },
      "best_strategy": "Butterfly",
      "market_conditions": {
        "iv_rank": 25.0,
        "range_expectation": 0.005,
        "gamma_environment": "Low volatility, high gamma",
        "enhancements_enabled": {
          "greeks_enabled": true,
          "advanced_gex_enabled": true,
          "volume_analysis_enabled": true
        }
      }
    }
  }
}
```

## Enhanced Indicators

### Greeks Analysis
- **Delta**: Directional exposure for Vertical spreads
- **Theta**: Time decay optimization for Butterflies
- **Vega**: Volatility risk assessment for Iron Condors
- **Source**: Production-ready `py_vollib_vectorized` library

### Advanced Gamma Exposure (GEX)
- **Net GEX**: Market maker positioning analysis
- **Gamma Walls**: Support/resistance levels
- **0DTE Multiplier**: 8x gamma sensitivity for same-day expiration
- **Methodology**: Based on jensolson/SPX-Gamma-Exposure

### Volume/Open Interest Analytics
- **V/OI Ratio**: Speculation vs hedging signals
- **Put/Call Ratios**: Market sentiment indicators
- **Unusual Activity**: Anomaly detection
- **Liquidity Score**: Strike concentration analysis

## Live Data Testing

### Yahoo Finance (Default)
- Free, no API key required
- 15-20 minute delay during market hours
- Good for testing and development

```bash
# In .env:
M8C_USE_MOCK_DATA=false
M8C_MARKET_DATA_PROVIDER=yahoo
```

### Interactive Brokers
- Real-time data
- Requires IB Gateway/TWS running
- Configure IB settings in .env

```bash
# In .env:
M8C_USE_MOCK_DATA=false
M8C_MARKET_DATA_PROVIDER=ib
M8C_IB_HOST=127.0.0.1
M8C_IB_PORT=7497
M8C_IB_CLIENT_ID=2
```

### Polygon.io
- Real-time data
- Requires API key
- Professional market data

```bash
# In .env:
M8C_USE_MOCK_DATA=false
M8C_MARKET_DATA_PROVIDER=polygon
M8C_POLYGON_API_KEY=your_api_key_here
```

## Integration with DiscordTrading

Add to your DiscordTrading system:

```python
from magic8_companion_integration import should_execute_strategy

# In your trade execution logic:
if should_execute_strategy(symbol, trade_type):
    execute_trade()
else:
    log.info(f"Skipping {trade_type} for {symbol} - not recommended")
```

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for detailed integration instructions.

## Strategy Scoring Logic

### Base Scoring (Original)
- **Butterfly**: Low IV (< 40%), tight ranges (< 0.6%)
- **Iron Condor**: Moderate IV (30-80%), range-bound markets
- **Vertical**: High IV (> 50%), wide ranges (> 1%)

### Enhanced Scoring (With Indicators)
- **Greeks Adjustments**: +/- 5-10 points based on strategy fit
- **GEX Adjustments**: +/- 3-8 points based on dealer positioning
- **Volume Adjustments**: +/- 2-5 points based on market sentiment

## Development

### Project Structure
```
Magic8-Companion/
├── magic8_companion/
│   ├── main.py              # Main application entry
│   ├── config.py            # Configuration management
│   ├── modules/
│   │   ├── market_analysis.py      # Market data analysis
│   │   ├── combo_scorer.py         # Base scoring logic
│   │   └── enhanced_combo_scorer.py # Enhanced scoring
│   ├── wrappers/            # Production system wrappers
│   │   ├── greeks_wrapper.py       # Greeks calculations
│   │   ├── gex_wrapper.py          # Gamma exposure
│   │   └── volume_wrapper.py       # Volume/OI analysis
│   └── utils/
│       └── scheduler.py     # Checkpoint scheduling
├── scripts/                 # Utility scripts
│   ├── setup_enhanced.sh    # Enhanced setup script
│   └── test_enhanced_indicators.py # Test enhanced features
├── data/                    # Output directory
└── tests/                   # Test suite
```

### Performance

Enhanced indicators add minimal overhead:
- Greeks calculation: ~10ms
- GEX analysis: ~15ms
- Volume/OI analysis: ~5ms
- Total additional latency: <50ms

## Troubleshooting

### "No market data available"
- Check internet connection
- Verify market hours (9:30 AM - 4:00 PM ET)
- Try different data provider

### "Import error"
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

### Enhanced indicators not working
- Check environment variables in .env
- Run `scripts/setup_enhanced.sh`
- Verify py_vollib_vectorized installed: `pip show py-vollib-vectorized`

### Live data issues
- Yahoo Finance: May have delays or rate limits
- IB: Ensure Gateway/TWS is running
- Check firewall settings

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

## Support

For issues or questions:
- Open a GitHub issue
- Check existing documentation
- Review test scripts for examples
