# Magic8-Companion

A simplified trade type recommendation engine that analyzes market conditions and outputs optimal strategy recommendations for the DiscordTrading system.

## Overview

Magic8-Companion is a lightweight companion service that:
- Analyzes market conditions at scheduled checkpoints (10:30, 11:00, 12:30, 14:45 ET)
- Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable
- Outputs recommendations to a JSON file for consumption by DiscordTrading
- Supports both mock data (for testing) and live market data via Yahoo Finance

## Architecture

```
Magic8 Discord → DiscordTrading → IB Execution
                      ↑
Magic8-Companion → recommendations.json
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/birddograbbit/Magic8-Companion.git
cd Magic8-Companion
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

Key configuration options:
- `M8C_USE_MOCK_DATA`: Set to `true` for testing, `false` for live data
- `M8C_MARKET_DATA_PROVIDER`: Choose `yahoo`, `ib`, or `polygon`
- `M8C_SUPPORTED_SYMBOLS`: List of symbols to analyze
- `M8C_CHECKPOINT_TIMES`: Times to run analysis

### 3. Test

**Test with mock data:**
```bash
python test_simplified.py
```

**Test with live market data:**
```bash
# Edit .env and set M8C_USE_MOCK_DATA=false
python test_live_data.py
```

### 4. Run

```bash
python -m magic8_companion.main
```

## Output Format

The system outputs recommendations to `data/recommendations.json`:

```json
{
  "timestamp": "2025-06-09T15:30:00Z",
  "checkpoint_time": "10:30 ET",
  "recommendations": {
    "SPX": {
      "preferred_strategy": "Butterfly",
      "score": 85.0,
      "confidence": "HIGH",
      "all_scores": {
        "Butterfly": 85.0,
        "Iron_Condor": 65.0,
        "Vertical": 50.0
      },
      "market_conditions": {
        "iv_rank": 25.0,
        "range_expectation": 0.005,
        "gamma_environment": "Low volatility, high gamma"
      },
      "rationale": "Low volatility environment (IV: 25%) with tight expected range (0.5%)"
    }
  }
}
```

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

### Butterfly
- Favored in low IV environments (< 40%)
- Tight expected ranges (< 0.6%)
- Gamma pinning conditions

### Iron Condor (Sonar)
- Moderate IV (30-80%)
- Range-bound markets
- Credit spread premium collection

### Vertical
- Higher IV environments (> 50%)
- Wide expected ranges (> 1%)
- Directional opportunities

## Development

### Project Structure
```
Magic8-Companion/
├── magic8_companion/
│   ├── main.py              # Main application entry
│   ├── config.py            # Configuration management
│   ├── modules/
│   │   ├── market_analysis.py   # Market data analysis
│   │   └── combo_scorer.py      # Strategy scoring logic
│   └── utils/
│       └── scheduler.py         # Checkpoint scheduling
├── integration/             # DiscordTrading integration
├── data/                   # Output directory
└── tests/                  # Test suite
```

### Adding New Data Providers

1. Implement data fetching in `market_analysis.py`
2. Add configuration options to `config.py`
3. Update `.env.example` with new settings

### Customizing Scoring Logic

Edit `combo_scorer.py` to adjust scoring parameters:
- Thresholds for each strategy type
- Bonus conditions
- Score weights

## Troubleshooting

### "No market data available"
- Check internet connection
- Verify market hours (9:30 AM - 4:00 PM ET)
- Try different data provider

### "Import error"
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

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
