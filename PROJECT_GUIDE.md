# Magic8 Trading System - Complete Guide

## 🎯 Overview

The Magic8 Trading System consists of two integrated components:
1. **Magic8-Companion** - Generates trading recommendations with confidence levels
2. **DiscordTrading** - Executes trades based on Discord signals filtered by Magic8 recommendations

**Key Rule**: Only trades with HIGH confidence recommendations from Magic8-Companion will be executed.

## 📁 Project Structure (After Cleanup)

```
/Users/jt/magic8/
├── Magic8-Companion/
│   ├── magic8_companion/          # Main application code
│   │   ├── main_simplified.py    # Main entry point
│   │   ├── config_simplified.py  # Configuration
│   │   ├── modules/              # Core modules
│   │   └── external/spx_gex/     # GEX analysis tools
│   ├── tests/
│   │   ├── test_simplified.py    # Quick functionality test
│   │   ├── test_live_data.py     # Live market data test
│   │   └── test_*.py            # Unit tests
│   ├── scripts/
│   │   ├── cleanup_project.py    # Project cleanup script
│   │   └── test_runner.py        # Unified test interface
│   ├── data/
│   │   └── recommendations.json  # Generated recommendations
│   └── docs/                     # Documentation
│
└── DiscordTrading/
    ├── discord_trading_bot.py    # Main Discord bot
    ├── magic8_integration.py     # Magic8 integration module
    ├── test_integration.py       # Integration tests
    ├── config.yaml              # Bot configuration
    └── order_manager.py         # Trade execution
```

## 🚀 Quick Start

### 1. Cleanup the Project

First, run the cleanup script to organize files:

```bash
cd /Users/jt/magic8/Magic8-Companion
python scripts/cleanup_project.py
```

This will:
- Create a backup of your current structure
- Move test files to proper locations
- Remove duplicate/unnecessary files
- Create a cleanup summary

### 2. Test the System

Use the unified test runner:

```bash
cd /Users/jt/magic8/Magic8-Companion
python scripts/test_runner.py
```

Menu options:
1. **Environment Check** - Verify setup is correct
2. **Quick Test** - Test Magic8 recommendation engine
3. **Live Data Test** - Test with real market data
4. **Integration Test** - Test Discord-Magic8 integration
5. **Monitor Live** - Watch recommendations in real-time
6. **Run All Tests** - Complete system verification

### 3. Live Testing

#### Schedule
Magic8-Companion runs at these times (ET):
- 10:30 AM
- 11:00 AM
- 12:30 PM
- 2:45 PM

#### Testing Process

1. **Start the Test Runner Monitor**:
   ```bash
   python scripts/test_runner.py
   # Select option 5 (Monitor Live System)
   ```

2. **Run Magic8-Companion** (in another terminal):
   ```bash
   cd /Users/jt/magic8/Magic8-Companion
   python -m magic8_companion.main_simplified
   ```

3. **Run DiscordTrading Bot** (in another terminal):
   ```bash
   cd /Users/jt/magic8/DiscordTrading
   python discord_trading_bot.py
   ```

4. **Observe the Flow**:
   - Magic8 generates recommendations → saved to `data/recommendations.json`
   - Monitor shows confidence levels and trade decisions
   - Only HIGH confidence trades proceed
   - DiscordTrading waits 1.5 minutes before checking recommendations

## 📊 Understanding Confidence Levels

| Confidence | Score Range | Action |
|------------|-------------|---------|
| HIGH       | 75-100      | ✅ Execute trade |
| MEDIUM     | 50-74       | ⚠️ Skip trade |
| LOW        | 0-49        | ❌ Skip trade |

## 🔧 Configuration

### Magic8-Companion
Create `.env` file:
```env
# Alpha Vantage API for market data
ALPHA_VANTAGE_API_KEY=your_key_here

# TradingView webhook (optional)
WEBHOOK_URL=your_webhook_url
WEBHOOK_ENABLED=false
```

### DiscordTrading
Edit `config.yaml`:
```yaml
magic8_companion:
  enabled: true
  recommendations_path: '../Magic8-Companion/data/recommendations.json'
  max_recommendation_age: 300  # 5 minutes
```

## 🧪 Testing Scenarios

### Scenario 1: HIGH Confidence Match
- Magic8 recommends Butterfly with HIGH confidence
- Discord signal: Butterfly
- **Result**: Trade executes ✅

### Scenario 2: MEDIUM Confidence
- Magic8 recommends Butterfly with MEDIUM confidence
- Discord signal: Butterfly
- **Result**: Trade skipped ⚠️

### Scenario 3: Strategy Mismatch
- Magic8 recommends Iron_Condor with HIGH confidence
- Discord signal: Butterfly
- **Result**: Trade skipped (wrong strategy) ❌

### Scenario 4: Stale Recommendation
- Magic8 recommendation > 5 minutes old
- Discord signal: Any
- **Result**: Trade proceeds (fallback) ✅

## 📝 Important Notes

1. **setup_spx_gex.py is NOT a duplicate** - It's a setup script that downloads GEX analysis tools

2. **Strategy Name Mapping**:
   - Discord "Sonar" → Magic8 "Iron_Condor"
   - Discord "Call Spread" → Magic8 "Vertical"
   - Discord "Put Spread" → Magic8 "Vertical"

3. **Timing Synchronization**:
   - Magic8 runs at scheduled times
   - DiscordTrading waits 1.5 minutes after signals
   - Recommendations expire after 5 minutes

4. **File Locations**:
   - Recommendations: `Magic8-Companion/data/recommendations.json`
   - Logs: Check both `Magic8-Companion/logs/` and `DiscordTrading/logs/`

## 🐛 Troubleshooting

### Issue: "Recommendations file not found"
- Ensure Magic8-Companion has run at least once
- Check the path in DiscordTrading's config.yaml

### Issue: "All trades being skipped"
- Verify Magic8 is generating HIGH confidence recommendations
- Check recommendation age (< 5 minutes)
- Ensure strategy names match after mapping

### Issue: "Integration test fails"
- Confirm both directories exist
- Check relative path in magic8_integration.py
- Verify .env files are present

## 🚦 Live Monitoring Commands

Monitor all components:
```bash
# Terminal 1 - Monitor recommendations
watch -n 5 cat /Users/jt/magic8/Magic8-Companion/data/recommendations.json

# Terminal 2 - Monitor Discord bot logs
tail -f /Users/jt/magic8/DiscordTrading/logs/discord_bot.log

# Terminal 3 - Use test runner monitor
python /Users/jt/magic8/Magic8-Companion/scripts/test_runner.py
```

## 📞 Support

For issues or questions:
1. Check the test runner diagnostics
2. Review log files in both projects
3. Ensure all dependencies are installed
4. Verify market hours for live testing

---

Last updated: June 2025
Version: 2.0 (Post-cleanup)
