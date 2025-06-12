# Magic8-Companion Integration Guide (Updated)

## Overview

This guide shows how Magic8-Companion integrates with DiscordTrading to provide intelligent trade filtering based on market conditions.

**Architecture:**
```
Discord Channel → DiscordTrading → Check Magic8-Companion → Execute/Skip Trade
                                 ↓
                   data/recommendations.json ← Magic8-Companion (scheduled analysis)
```

## How It Works

1. **Magic8-Companion** runs on a schedule (10:30, 11:00, 12:30, 14:45, etc.) and analyzes market conditions
2. It outputs recommendations to `data/recommendations.json` with preferred strategies and confidence levels
3. **DiscordTrading** monitors Discord channels for trade signals
4. When a trade signal arrives, DiscordTrading checks Magic8-Companion's recommendations
5. Only trades with HIGH confidence recommendations proceed (configurable)

## Phase 1: Magic8-Companion Setup

### 1. Run Magic8-Companion

```bash
cd Magic8-Companion
python -m magic8_companion
```

This will:
- Run at scheduled checkpoints throughout the day
- Analyze market conditions for SPX, SPY, QQQ, RUT
- Generate `data/recommendations.json` with strategy recommendations

### 2. Output Format

Magic8-Companion generates recommendations in this format:

```json
{
  "timestamp": "2025-06-11T14:45:00Z",
  "checkpoint_time": "14:45 ET",
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

## Phase 2: DiscordTrading Integration (Already Built!)

### 1. Enable Magic8 Integration

In DiscordTrading's `config.yaml`:

```yaml
# Magic8-Companion Integration
magic8_companion:
  enabled: true  # Set to true to enable filtering
  recommendations_path: "../Magic8-Companion/data/recommendations.json"
  max_recommendation_age: 300  # 5 minutes - ignore stale recommendations
```

### 2. How DiscordTrading Uses Recommendations

The integration is already built into DiscordTrading (`magic8_integration.py`):

- **Strategy Mapping**: Maps Discord signals to Magic8 strategies
  - "Sonar" → "Iron_Condor"
  - "Butterfly" → "Butterfly"
  - "Vertical" → "Vertical"
  - "Call Spread"/"Put Spread" → "Vertical"

- **Decision Logic**:
  - If `confidence != "HIGH"`, trade is skipped
  - If preferred strategy doesn't match signal, trade is skipped
  - If recommendation is older than `max_recommendation_age`, it's ignored

### 3. Example Flow

1. **10:30 ET**: Magic8-Companion runs and recommends:
   - SPX: Butterfly (HIGH confidence)
   - SPY: Iron_Condor (MEDIUM confidence)

2. **10:35 ET**: Discord signal arrives:
   ```
   SELL -1 Butterfly SPX 100 11 Jun 25 6000/6010/6020 CALL @1.0 LMT
   ```

3. **DiscordTrading checks**:
   - ✅ SPX Butterfly matches HIGH confidence recommendation
   - Trade executes

4. **10:40 ET**: Another Discord signal:
   ```
   SELL -1 Vertical SPX 100 11 Jun 25 6000/6005 CALL @0.5 LMT
   ```

5. **DiscordTrading checks**:
   - ❌ SPX Vertical doesn't match recommended Butterfly
   - Trade is skipped with log: "Magic8 recommends Butterfly not Vertical"

## Testing the Integration

### 1. Test Both Systems Together

```bash
# Terminal 1: Run Magic8-Companion
cd Magic8-Companion
python -m magic8_companion

# Terminal 2: Run DiscordTrading
cd DiscordTrading
python discord_trading_bot.py
```

### 2. Monitor Integration

Watch for these log messages in DiscordTrading:

```
# Successful recommendation check:
2025-06-11 10:35:15 - INFO - Magic8 recommendation for SPX: Butterfly (HIGH confidence)
2025-06-11 10:35:15 - INFO - Magic8 confirms Butterfly with HIGH confidence

# Skipped trade:
2025-06-11 10:40:22 - INFO - Magic8 recommendation for SPX: Butterfly (HIGH confidence)
2025-06-11 10:40:22 - INFO - Magic8 recommends Butterfly not Vertical (HIGH confidence)
2025-06-11 10:40:22 - INFO - Skipping trade: Magic8 recommends Butterfly not Vertical
```

### 3. Test Without Integration

To test DiscordTrading without Magic8 filtering:

```yaml
# In config.yaml
magic8_companion:
  enabled: false  # Disables Magic8 checking
```

## Configuration Reference

### Magic8-Companion Settings (.env)

```bash
# Core Settings
M8C_OUTPUT_FILE_PATH=data/recommendations.json
M8C_SUPPORTED_SYMBOLS=["SPX", "SPY", "QQQ", "RUT"]
M8C_CHECKPOINT_TIMES=["10:30", "11:00", "12:30", "14:45", ...]
M8C_MIN_RECOMMENDATION_SCORE=70
M8C_MIN_SCORE_GAP=15

# Data Source
M8C_USE_MOCK_DATA=false        # Use real market data
M8C_USE_IBKR_DATA=true        # Use Interactive Brokers
M8C_IBKR_HOST=127.0.0.1
M8C_IBKR_PORT=7497

# Enhanced Indicators
M8C_ENABLE_GREEKS=true
M8C_ENABLE_ADVANCED_GEX=true
M8C_ENABLE_VOLUME_ANALYSIS=true
```

### DiscordTrading Settings (config.yaml)

```yaml
magic8_companion:
  enabled: true
  recommendations_path: "../Magic8-Companion/data/recommendations.json"
  max_recommendation_age: 300  # seconds
```

## Troubleshooting

### Issue: "No recommendations file found"
- Ensure Magic8-Companion is running and generating files
- Check the path in `recommendations_path` is correct
- Verify file permissions

### Issue: "Recommendation too old"
- Magic8-Companion should be running throughout the trading day
- Check that checkpoints are configured for your trading times
- Increase `max_recommendation_age` if needed

### Issue: All trades are being skipped
- Check that Magic8-Companion is generating HIGH confidence recommendations
- Verify the strategy names match between systems
- Enable debug logging to see recommendation details

### Debug Logging

In DiscordTrading:
```yaml
system:
  log_level: DEBUG
```

This will show detailed Magic8 recommendation checks.

## Production Deployment

### Option 1: Systemd Services (Linux)

Create service files for both systems to run automatically.

### Option 2: Screen/Tmux Sessions

```bash
# Start Magic8-Companion in screen
screen -S magic8
cd Magic8-Companion
python -m magic8_companion

# Start DiscordTrading in another screen
screen -S discord
cd DiscordTrading
python discord_trading_bot.py
```

### Option 3: Docker Compose

Use the provided docker-compose setup for containerized deployment.

## Summary

The integration is already built and ready to use:

1. ✅ Magic8-Companion generates recommendations on schedule
2. ✅ DiscordTrading has built-in integration (`magic8_integration.py`)
3. ✅ Simple configuration in both systems
4. ✅ Only HIGH confidence trades execute (configurable)
5. ✅ Full logging and debugging support

Just enable the integration in `config.yaml` and ensure both systems are running!