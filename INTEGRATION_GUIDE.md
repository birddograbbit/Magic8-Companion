# Magic8-Companion Integration Guide

## Overview

This guide shows how to integrate the simplified Magic8-Companion with the DiscordTrading system for intelligent trade type filtering.

**Architecture:**
```
Magic8-Companion (Simplified) → recommendations.json → DiscordTrading (Enhanced) → IB Execution
```

## Phase 1: Simplified Magic8-Companion Setup

### 1. Dependencies

```bash
pip install pydantic-settings pytz
```

### 2. Configuration

Create `.env` file:
```bash
# Magic8-Companion Configuration
M8C_OUTPUT_FILE_PATH=data/recommendations.json
M8C_SUPPORTED_SYMBOLS=["SPX", "SPY", "QQQ", "RUT"]
M8C_CHECKPOINT_TIMES=["10:30", "11:00", "12:30", "14:45"]
M8C_MIN_RECOMMENDATION_SCORE=70
M8C_MIN_SCORE_GAP=15
M8C_USE_MOCK_DATA=true
```

### 3. Test the System

```bash
# Test the recommendation engine
python test_simplified.py

# Run with scheduled checkpoints
python -m magic8_companion.main_simplified
```

### 4. Expected Output

The system will create `data/recommendations.json`:

```json
{
  "timestamp": "2025-06-09T17:30:00Z",
  "checkpoint_time": "10:30 ET",
  "recommendations": {
    "SPX": {
      "preferred_strategy": "Butterfly",
      "score": 82.0,
      "confidence": "MEDIUM",
      "all_scores": {
        "Butterfly": 82.0,
        "Iron_Condor": 65.0,
        "Vertical": 45.0
      },
      "market_conditions": {
        "iv_rank": 65.0,
        "range_expectation": 0.008,
        "gamma_environment": "Range-bound, moderate gamma"
      },
      "rationale": "Low volatility environment (IV: 65.0%) with tight expected range (0.8%)"
    }
  }
}
```

## Phase 2: DiscordTrading Integration

### 1. Copy Integration Module

Copy `integration/magic8_companion_integration.py` to your DiscordTrading project directory.

### 2. Modify DiscordTrading Configuration

Update your `config.yaml` to include Magic8-Companion filtering:

```yaml
# Add to your existing config.yaml
system:
  use_new_architecture: true
  use_magic8_companion: true  # New flag
  magic8_recommendations_file: "../Magic8-Companion/data/recommendations.json"
  
# Your existing symbols configuration remains the same
symbols:
  SPX:
    enabled: true
    channel_id: "1048242197029458040"
    # ... rest of config
```

### 3. Enhance DiscordTrading Bot

Add to your `discord_trading_bot.py`:

```python
# Add import at top
from magic8_companion_integration import should_execute_strategy, log_current_recommendations

class DiscordTradingBot:
    def __init__(self, config_path: str = "config.yaml"):
        # ... existing init code ...
        
        # Log Magic8-Companion status on startup
        log_current_recommendations()
    
    def _process_message(self, message: Dict[str, Any], symbol: str, channel_id: str, now_et: datetime):
        """Enhanced message processing with Magic8-Companion filtering."""
        # ... existing code until trade execution ...
        
        for instruction in instructions:
            trade_type = instruction.get('trade_type')
            
            # ENHANCED: Check Magic8-Companion recommendation
            if not should_execute_strategy(symbol, trade_type):
                logger.info(f"Skipping {trade_type} for {symbol} - not recommended by Magic8-Companion")
                continue
            
            # ... rest of existing execution logic ...
```

### 4. Alternative: Simple Integration

For quick testing, add this simple check before trade execution:

```python
import json
from pathlib import Path

def is_strategy_recommended(symbol: str, strategy: str) -> bool:
    """Simple check for Magic8-Companion recommendation."""
    try:
        rec_file = Path("../Magic8-Companion/data/recommendations.json")
        if not rec_file.exists():
            return True  # Allow if no recommendations file
            
        with open(rec_file, 'r') as f:
            data = json.load(f)
            
        symbol_rec = data.get("recommendations", {}).get(symbol)
        if not symbol_rec:
            return True  # Allow if no specific recommendation
            
        preferred = symbol_rec.get("preferred_strategy")
        strategy_map = {"Sonar": "Iron_Condor", "Butterfly": "Butterfly", "Vertical": "Vertical"}
        
        return strategy_map.get(strategy) == preferred
        
    except:
        return True  # Allow on error

# Use before trade execution:
if is_strategy_recommended(symbol, trade_type):
    # Execute trade
    pass
else:
    logger.info(f"Skipping {trade_type} - not recommended by Magic8-Companion")
```

## Testing Integration

### 1. Run Magic8-Companion

```bash
cd Magic8-Companion
python -m magic8_companion.main_simplified
```

### 2. Check Recommendations

```bash
cat data/recommendations.json
```

### 3. Run DiscordTrading with Integration

```bash
cd DiscordTrading
python discord_trading_bot.py
```

### 4. Expected Behavior

You should see logs like:
```
2025-06-09 10:30:15 - INFO - 📊 Magic8-Companion Recommendations (10:30 ET):
2025-06-09 10:30:15 - INFO -   SPX: Butterfly (Score: 82, MEDIUM)
2025-06-09 10:31:20 - INFO - ✅ SPX Butterfly: RECOMMENDED by Magic8-Companion (MEDIUM confidence)
2025-06-09 10:31:25 - INFO - 🚫 SPX Vertical: NOT recommended by Magic8-Companion (prefers Butterfly)
```

## Configuration Options

### Magic8-Companion Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `M8C_OUTPUT_FILE_PATH` | `data/recommendations.json` | Output file path |
| `M8C_SUPPORTED_SYMBOLS` | `["SPX", "SPY", "QQQ", "RUT"]` | Symbols to analyze |
| `M8C_CHECKPOINT_TIMES` | `["10:30", "11:00", "12:30", "14:45"]` | Analysis times |
| `M8C_MIN_RECOMMENDATION_SCORE` | `70` | Minimum score to recommend |
| `M8C_MIN_SCORE_GAP` | `15` | Minimum gap between best/second-best |
| `M8C_USE_MOCK_DATA` | `true` | Use mock data for testing |

### DiscordTrading Integration Modes

**1. Strict Mode:** Only execute recommended strategies
```python
if should_execute_strategy(symbol, trade_type):
    execute_trade()
# Skip if not recommended
```

**2. Advisory Mode:** Log recommendations but allow all trades
```python
if should_execute_strategy(symbol, trade_type):
    logger.info(f"✅ {trade_type} RECOMMENDED")
else:
    logger.warning(f"⚠️ {trade_type} NOT RECOMMENDED")
execute_trade()  # Execute anyway
```

**3. Hybrid Mode:** Reduce quantity for non-recommended trades
```python
if should_execute_strategy(symbol, trade_type):
    quantity = full_quantity
else:
    quantity = full_quantity // 2  # Half quantity
    logger.info(f"⚠️ Reduced quantity for non-recommended {trade_type}")
```

## Troubleshooting

### Common Issues

1. **No recommendations file**
   ```bash
   # Ensure Magic8-Companion is running and generating files
   ls -la data/recommendations.json
   ```

2. **Import errors**
   ```bash
   # Ensure Python path includes both projects
   export PYTHONPATH="${PYTHONPATH}:/path/to/Magic8-Companion"
   ```

3. **Stale recommendations**
   ```bash
   # Check file timestamp
   stat data/recommendations.json
   ```

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('magic8_companion_integration').setLevel(logging.DEBUG)
```

## Production Deployment

### 1. Run Both Systems

```bash
# Terminal 1: Magic8-Companion
cd Magic8-Companion
python -m magic8_companion.main_simplified

# Terminal 2: DiscordTrading
cd DiscordTrading  
python discord_trading_bot.py
```

### 2. Docker Setup (Optional)

```yaml
# docker-compose.yml
version: '3.8'
services:
  magic8-companion:
    build: ./Magic8-Companion
    volumes:
      - ./shared:/app/data
    
  discord-trading:
    build: ./DiscordTrading
    volumes:
      - ./shared:/app/data
    depends_on:
      - magic8-companion
```

### 3. Monitoring

Monitor both systems:
```bash
tail -f Magic8-Companion/logs/magic8_companion.log
tail -f DiscordTrading/logs/discord_trading_bot.log
```

## Next Steps

1. **Test with paper trading** to validate integration
2. **Monitor recommendation accuracy** over time
3. **Enhance scoring algorithms** based on performance
4. **Add real market data** feeds to replace mock data
5. **Implement exit signal generation** for position management

This integration provides a clean separation of concerns while enabling intelligent trade type filtering based on market conditions.
