# Magic8-Companion

A simplified trade type recommendation engine that analyzes market conditions and outputs optimal strategy recommendations for the DiscordTrading system.

## 📚 Documentation

- **[CONSOLIDATED_GUIDE.md](docs/CONSOLIDATED_GUIDE.md)** - Complete system setup and operation guide
- **[ML_INTEGRATION_GUIDE.md](docs/ML_INTEGRATION_GUIDE.md)** - **NEW!** MLOptionTrading ML integration
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - DiscordTrading integration details
- **[ENHANCED_INDICATORS.md](ENHANCED_INDICATORS.md)** - Enhanced features documentation
- **[SCORING_SYSTEM.md](SCORING_SYSTEM.md)** - Scoring logic reference
- **[IBKR_TROUBLESHOOTING.md](IBKR_TROUBLESHOOTING.md)** - Interactive Brokers connection troubleshooting
- **[ENHANCED_GAMMA_MIGRATION_PLAN.md](docs/ENHANCED_GAMMA_MIGRATION_PLAN.md)** - Migration planning document
- **[ENHANCED_GAMMA_MIGRATION_GUIDE.md](docs/ENHANCED_GAMMA_MIGRATION_GUIDE.md)** - Current migration steps

## 🚀 New Features

### ML Enhancement Integration (NEW!)
- **Two-Stage ML Models**: Direction + Volatility prediction from MLOptionTrading
- **35% ML / 65% Rules**: Balanced approach combining ML with proven rules
- **2.5 Years Training Data**: Based on profitable Discord trading history
- See **[ML_INTEGRATION_GUIDE.md](docs/ML_INTEGRATION_GUIDE.md)** for setup
- **Phase 2: 5-Minute Predictions**: Enable real-time ML by setting `M8C_ENABLE_ML_5MIN=true`

### Gamma Enhancement Integration
- Integration with MLOptionTrading for gamma exposure analysis
- Real-time gamma adjustments to scoring (+/- 20 points max)
- Support for gamma walls, flip points, and regime detection

### Enhanced Indicators (Optional)
- **Greeks Analysis**: Delta, Theta, Vega calculations
- **Advanced Gamma Exposure**: Net GEX, gamma walls, 0DTE multipliers
- **Volume/OI Analytics**: Market sentiment and liquidity analysis

### IBKR Connection Improvements (June 17, 2025)
- **Automatic SPX/SPXW handling**: Supports both symbols for 0DTE options
- **Multiple exchange fallback**: Tries SMART, CBOE, and other exchanges
- **Better error handling**: Improved logging and automatic recovery

## Overview

Magic8-Companion is a lightweight companion service that:
- Analyzes market conditions at scheduled checkpoints (10:30, 11:00, 12:30, 14:45 ET)
- Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable
- Integrates with MLOptionTrading for ML-enhanced predictions
- Outputs recommendations to a JSON file for consumption by DiscordTrading
- Supports both mock data (for testing) and live market data

## Architecture

```
Discord Trading History → MLOptionTrading (ML Training)
                                    ↓
                           Two-Stage ML Models
                                    ↓
Magic8-Companion (Rule Scoring) ← ML Enhanced Scoring (35%)
                                    ↓
                           recommendations.json
                                    ↓
                           DiscordTrading
```

## Quick Start

For complete setup instructions, see **[CONSOLIDATED_GUIDE.md](docs/CONSOLIDATED_GUIDE.md)**

### 1. Basic Setup

```bash
git clone https://github.com/birddograbbit/Magic8-Companion.git
cd Magic8-Companion
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
nano .env
```

Key configuration options:
- `M8C_USE_MOCK_DATA`: Set to `false` for live data
- `M8C_ENABLE_ML_INTEGRATION`: Set to `true` for ML predictions
- `M8C_ML_WEIGHT`: Adjust ML influence (0.0-1.0, default `0.35`)
- `M8C_ML_PATH`: Path to the `MLOptionTrading` repository
- `M8C_ENABLE_GAMMA_INTEGRATION`: Set to `true` for gamma enhancements
- `M8C_MIN_RECOMMENDATION_SCORE`: Lower to 65 for more recommendations

### 3. Test

```bash
# Test basic functionality
python scripts/test_runner.py

# Test with ML integration
cp ../MLOptionTrading/magic8_ml_integration.py ./
python scripts/test_runner.py  # Select option 4

# Test with gamma integration
./start_magic8_enhanced.sh
```

Set the `MAGIC8_ROOT` environment variable if your repository lives outside the
standard directory layout so the test runner can locate the project correctly.

## Output Format

The system outputs recommendations to `data/recommendations.json`:

```json
{
  "timestamp": "2025-06-16T15:30:00Z",
  "checkpoint_time": "10:30 ET",
  "enhanced_indicators": true,
  "recommendations": {
    "SPX": {
      "strategies": {
        "Butterfly": {
          "score": 85.0,
          "confidence": "HIGH",
          "should_trade": true,
          "rationale": "Low volatility environment with gamma support",
          "gamma_adjustment": 15,
          "ml_contribution": 25
        }
      },
      "best_strategy": "Butterfly",
      "market_conditions": {
        "gamma_regime": "positive",
        "gamma_flip": 6000,
        "call_wall": 6050,
        "put_wall": 5950
      }
    }
  }
}
```
##RUN:
python -m magic8_companion.unified_main

## Integration Points

### With MLOptionTrading
- Reads trained models from `../MLOptionTrading/models/`
- Applies ML predictions to enhance rule-based scoring
- Supports real-time feature engineering
- See **[ML_INTEGRATION_GUIDE.md](docs/ML_INTEGRATION_GUIDE.md)** for details

### With DiscordTrading
- Outputs recommendations to `data/recommendations.json`
- Only HIGH confidence trades are executed
- Strategy name mapping handled automatically

## Live Data Providers

### Yahoo Finance (Default)
- Free, no API key required
- 15-20 minute delay
- Good for testing

### Interactive Brokers
- Real-time data
- Requires IB Gateway/TWS
- Best for production
- See **[IBKR_TROUBLESHOOTING.md](IBKR_TROUBLESHOOTING.md)** for setup help

### Polygon.io
- Professional market data
- Requires API key
- Alternative to IB

## Project Structure

```
Magic8-Companion/
├── magic8_companion/        # Source code
│   ├── modules/            # Core scoring modules
│   ├── wrappers/           # Integration wrappers
│   └── utils/              # Utilities
├── scripts/                # Test and utility scripts
├── docs/                   # Documentation
│   ├── CONSOLIDATED_GUIDE.md     # Complete system guide
│   └── ML_INTEGRATION_GUIDE.md   # ML integration guide
├── data/                   # Output directory
└── tests/                  # Unit tests
```

## Troubleshooting

For detailed troubleshooting, see:
- **[CONSOLIDATED_GUIDE.md](docs/CONSOLIDATED_GUIDE.md)** - General issues
- **[ML_INTEGRATION_GUIDE.md](docs/ML_INTEGRATION_GUIDE.md)** - ML integration issues
- **[IBKR_TROUBLESHOOTING.md](IBKR_TROUBLESHOOTING.md)** - IBKR-specific issues

Common issues:
- **No recommendations**: Lower `M8C_MIN_RECOMMENDATION_SCORE` to 65
- **No ML predictions**: Ensure MLOptionTrading models are trained
- **No gamma data**: Ensure MLOptionTrading is running
- **All trades skipped**: Check confidence thresholds and strategy mapping
- **IBKR connection errors**: See IBKR troubleshooting guide

## Testing

Use the unified test runner for comprehensive testing:

```bash
python scripts/test_runner.py
```

Options:
1. Environment Check
2. Quick Test
3. Live Data Test
4. Integration Test (includes ML)
5. Monitor Live System

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check **[CONSOLIDATED_GUIDE.md](docs/CONSOLIDATED_GUIDE.md)** first
- For ML issues, see **[ML_INTEGRATION_GUIDE.md](docs/ML_INTEGRATION_GUIDE.md)**
- For IBKR issues, see **[IBKR_TROUBLESHOOTING.md](IBKR_TROUBLESHOOTING.md)**
- Open a GitHub issue
- Review test scripts for examples
