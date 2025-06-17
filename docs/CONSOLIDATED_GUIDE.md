# Magic8-Companion Consolidated Guide

This guide consolidates all essential information for running the Magic8-Companion system with Gamma Enhancement and integration with DiscordTrading.

## Table of Contents
1. [System Overview](#system-overview)
2. [Complete Setup Guide](#complete-setup-guide)
3. [Production Workflow](#production-workflow)
4. [Integration Details](#integration-details)
5. [Troubleshooting](#troubleshooting)
6. [Important Configuration Notes](#important-configuration-notes)

## System Overview

### Architecture
```
MLOptionTrading (Gamma Analysis) → gamma_adjustments.json
                                         ↓
Magic8-Companion (Enhanced Scoring) → recommendations.json
                                         ↓
DiscordTrading (Trade Execution) ← Discord Signals
```

### Key Components
- **MLOptionTrading**: Provides gamma exposure analysis and market structure insights
- **Magic8-Companion**: Core scoring engine with gamma enhancements
- **DiscordTrading**: Executes trades based on Discord signals filtered by Magic8 recommendations

## Complete Setup Guide

### 1. Environment Setup

#### Directory Structure
```bash
~/magic8/
├── MLOptionTrading/       # Gamma analysis system
├── Magic8-Companion/       # This repository
└── DiscordTrading/        # Discord bot execution
```

#### Initial Setup (One-time)
```bash
# Clone repositories
cd ~/magic8
git clone https://github.com/birddograbbit/MLOptionTrading.git
git clone https://github.com/birddograbbit/Magic8-Companion.git
git clone https://github.com/birddograbbit/DiscordTrading.git

# Setup MLOptionTrading
cd MLOptionTrading
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python setup_gamma_enhancement.py

# Setup Magic8-Companion
cd ../Magic8-Companion
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

#### Magic8-Companion (.env)

**CRITICAL**: You must set the system complexity mode to use IBKR data!

```bash
# CRITICAL: Set system complexity mode (simple uses mock data)
M8C_SYSTEM_COMPLEXITY=enhanced  # REQUIRED for IBKR data!

# Core Settings
M8C_OUTPUT_FILE_PATH=data/recommendations.json
M8C_SUPPORTED_SYMBOLS=["SPX", "SPY", "QQQ", "NDX", "RUT"]
M8C_CHECKPOINT_TIMES=["10:30", "11:00", "12:30", "14:45"]
M8C_MIN_RECOMMENDATION_SCORE=65  # Reduced from 70 for more recommendations
M8C_MIN_SCORE_GAP=15

# Market Data
M8C_USE_MOCK_DATA=false
M8C_MARKET_DATA_PROVIDER=ib  # Options: yahoo, ib, polygon

# Enhanced Features
M8C_ENABLE_ENHANCED_INDICATORS=false  # Keep false for gamma-only
M8C_ENABLE_GAMMA_INTEGRATION=true

# IBKR Settings (if using IB data)
M8C_USE_IBKR_DATA=true
M8C_IBKR_HOST=127.0.0.1
M8C_IBKR_PORT=7497  # 7497 for paper, 7496 for live
M8C_IBKR_CLIENT_ID=111
M8C_IBKR_FALLBACK_TO_YAHOO=true

# Paths
M8C_GAMMA_ADJUSTMENTS_PATH=../MLOptionTrading/data/gamma_adjustments.json
```

#### MLOptionTrading Configuration
```bash
# In MLOptionTrading/analysis/gamma/config.py or .env
SYMBOLS = ["SPX", "SPY", "QQQ"]
ANALYSIS_TIMES = ["10:30", "11:00", "12:30", "14:45"]
OUTPUT_PATH = "data/gamma_adjustments.json"
```

#### DiscordTrading (config.yaml)
```yaml
magic8_companion:
  enabled: true
  recommendations_path: "../Magic8-Companion/data/recommendations.json"
  max_recommendation_age: 300  # 5 minutes
```

### 3. Test the System

```bash
# Test gamma integration
cd ~/magic8/MLOptionTrading
python test_gamma_integration.py

# Test Magic8 with gamma enhancement
cd ~/magic8/Magic8-Companion
python scripts/test_runner.py
# Select option 2 for quick test
```

If your directory layout differs, set the `MAGIC8_ROOT` environment variable to
the Magic8-Companion folder before running the script.

## Production Workflow

### Starting the System (3 Terminals)

#### Terminal 1: Gamma Analysis
```bash
cd ~/magic8/MLOptionTrading
source venv/bin/activate
python gamma_scheduler.py --mode scheduled
```

#### Terminal 2: Magic8 Enhanced
```bash
cd ~/magic8/Magic8-Companion
source .venv/bin/activate
# IMPORTANT: Use this command format
python -m magic8_companion
# DO NOT use: python -m magic8_companion.main
```

#### Terminal 3: Discord Trading (Optional)
```bash
cd ~/magic8/DiscordTrading
source venv/bin/activate
python discord_trading_bot.py
```

### Monitoring

#### Watch Gamma Adjustments
```bash
watch -n 5 cat ~/magic8/MLOptionTrading/data/gamma_adjustments.json
```

#### Watch Recommendations
```bash
watch -n 5 cat ~/magic8/Magic8-Companion/data/recommendations.json
```

#### Check Logs
```bash
# Magic8 logs
tail -f ~/magic8/Magic8-Companion/logs/magic8_*.log

# MLOptionTrading logs
tail -f ~/magic8/MLOptionTrading/logs/gamma_*.log
```

## Integration Details

### Gamma Score Adjustments

The gamma integration provides the following scoring adjustments:

#### Butterfly Strategy
- **Positive gamma regime**: +15 points (prefers dampened volatility)
- **Near gamma walls**: +10 points (pinning potential)
- **Maximum adjustment**: +20 points

#### Iron Condor Strategy
- **Positive gamma regime**: +10 points (range-bound conditions)
- **Low expected move**: +15 points (tight range expected)
- **Maximum adjustment**: +20 points

#### Vertical Strategy
- **Negative gamma regime**: +10 points (amplified moves)
- **Near gamma flip**: +15 points (breakout potential)
- **Maximum adjustment**: +20 points

### Strategy Mapping (Discord → Magic8)
- "Sonar" → "Iron_Condor"
- "Butterfly" → "Butterfly"
- "Vertical" → "Vertical"
- "Call Spread"/"Put Spread" → "Vertical"

### Confidence Levels
| Confidence | Score Range | Action |
|------------|-------------|---------|
| HIGH       | 75-100      | ✅ Execute trade |
| MEDIUM     | 50-74       | ⚠️ Skip trade |
| LOW        | 0-49        | ❌ Skip trade |

## Troubleshooting

### Common Issues and Solutions

#### "Using cached MOCK data" despite IBKR configuration
**Solution**: Add `M8C_SYSTEM_COMPLEXITY=enhanced` to your .env file
- The system defaults to "standard" mode
- Only "enhanced" mode uses real market data with IBKR
- "simple" mode always uses mock data

#### "No gamma adjustments found"
```bash
# Check if gamma analysis is running
ps aux | grep gamma_scheduler

# Verify gamma adjustments file exists
ls -la ~/magic8/MLOptionTrading/data/gamma_adjustments.json

# Check gamma analysis logs
tail -n 50 ~/magic8/MLOptionTrading/logs/gamma_*.log
```

#### "No recommendations generated"
- Verify market hours (9:30 AM - 4:00 PM ET)
- Check minimum score thresholds in .env
- Ensure market data is available
- Review logs for errors

#### "All trades being skipped"
- Lower `M8C_MIN_RECOMMENDATION_SCORE` to 65 or 60
- Check that gamma integration is enabled
- Verify strategy name mapping is correct
- Ensure recommendations aren't stale (>5 minutes old)

#### IBKR Connection Issues
```bash
# Verify IB Gateway/TWS is running
netstat -an | grep 7497  # Should show LISTENING

# Check IB settings
# - Enable API connections
# - Set socket port to 7497 (paper) or 7496 (live)
# - Allow connections from 127.0.0.1
```

#### NaN/Invalid Data Issues
- Ensure open interest data is available (may be 0 at market open)
- Volume data might be NaN outside market hours
- Use fallback values in configuration

## Important Configuration Notes

### System Complexity Modes
- **simple**: Uses mock data only, basic features
- **standard**: Production features, but may still use mock data
- **enhanced**: Full features with IBKR data integration (RECOMMENDED)

### SPX vs SPXW Options
- IBKR uses "SPXW" for weekly SPX options
- The system automatically handles this mapping
- Both "SPX" and "SPXW" are treated as SPX internally

### Strike Limits
Different symbols have different strike width requirements:
- **SPX/SPXW**: 5-point strikes (6000, 6005, 6010...)
- **SPY**: 1-point strikes with half-dollars near ATM
- **QQQ**: 1-point strikes
- **NDX**: 25-point strikes
- **RUT**: 5-point strikes

### Timing Synchronization
- Gamma analysis runs at checkpoint times
- Magic8 runs 30 seconds after checkpoints
- DiscordTrading waits 1.5 minutes after signals
- Recommendations expire after 5 minutes

### Safety Features
- Gamma adjustments are capped at ±20 points
- Only HIGH confidence trades execute
- Stale recommendations are ignored
- Kill switch available via Discord commands

## Quick Reference Commands

### Start Everything
```bash
# Quick start script (create this)
#!/bin/bash
# start_all.sh
tmux new-session -d -s gamma "cd ~/magic8/MLOptionTrading && source venv/bin/activate && python gamma_scheduler.py --mode scheduled"
tmux new-session -d -s magic8 "cd ~/magic8/Magic8-Companion && source .venv/bin/activate && python -m magic8_companion"
tmux new-session -d -s discord "cd ~/magic8/DiscordTrading && source venv/bin/activate && python discord_trading_bot.py"
echo "All systems started. Use 'tmux attach -t [gamma|magic8|discord]' to view"
```

### Stop Everything
```bash
tmux kill-session -t gamma
tmux kill-session -t magic8
tmux kill-session -t discord
```

### View Sessions
```bash
tmux ls  # List sessions
tmux attach -t magic8  # Attach to specific session
```

## Performance Tips

1. **Reduce Over-Conservative Behavior**
   - Set `M8C_MIN_RECOMMENDATION_SCORE=60`
   - Enable gamma integration for score boosts
   - Consider wider checkpoint times

2. **Optimize Data Collection**
   - Use IBKR for real-time data during market hours
   - Yahoo Finance is sufficient for testing
   - Cache option chains to reduce API calls

3. **Monitor System Health**
   - Check logs regularly for errors
   - Monitor recommendation generation rate
   - Track actual vs recommended trades

---

Last Updated: June 2025
Version: Post-cleanup with Gamma Integration - Fixed IBKR data issue