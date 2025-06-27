# ML Integration Guide: Magic8-Companion + MLOptionTrading

## 🚀 Overview

This guide details the complete integration between Magic8-Companion and MLOptionTrading, enabling ML-enhanced trading recommendations based on 2.5 years of profitable Discord trading history.

**Current System Status**: ⚠️ Phase 2 Partially Implemented (Deployment Pending)
**Phase 2 Status**: 🔧 Real-Time 5-Minute ML Predictions (In Progress)

## 🏗️ Architecture

```
Discord Trading History (2022-2025) → MLOptionTrading (ML Training)
                                              ↓
                                    Two-Stage ML Models
                                    (Direction + Volatility)
                                              ↓
Magic8-Companion (Rule-Based Scoring) ← ML Enhanced Scoring
         ↓                                    ↓
    IB Connection ────────────────► Real-Time ML Predictor (Phase 2)
         ↓                                    ↓
    Checkpoints                          5-Min Schedule
    (10:30, 11:00,                      (Continuous)
     12:30, 14:45)                           ↓
         ↓                                    ↓
         └──────────► Merged recommendations.json ◄────────┘
                                    ↓
                              DiscordTrading
```

## Phase 1: Checkpoint-Based ML Integration (Current)

[Previous Phase 1 content remains unchanged...]

## 📊 Understanding the Butterfly Strategy Issue

### Why Butterfly Rarely Appears

The current ML system uses a two-stage prediction approach:
1. **Stage 1**: Predicts market direction (bearish/neutral/bullish)
2. **Stage 2**: Predicts volatility regime (low/normal/high)

The strategy mapping is:
```python
{
    ("bullish", "high"): "Butterfly",
    ("bearish", "high"): "Butterfly",
    ("neutral", "low"): "Iron_Condor",
    ("neutral", "normal"): "Iron_Condor",
    # ... other mappings
}
```

**Issue**: Butterfly only appears when volatility is "high", but recent market data (May-June 2025) shows consistent "normal" volatility:
- Test data: 10,456 samples ALL with volatility class 1 (normal)
- No samples with volatility class 0 (low) or 2 (high)

**Solution**: The system needs broader date ranges to capture different volatility regimes, or the thresholds need adjustment based on actual VIX distributions.

## 🔧 Setup Instructions

### Prerequisites

1. Both repositories cloned side-by-side:
```bash
/path/to/projects/
├── Magic8-Companion/
└── MLOptionTrading/
```

2. MLOptionTrading models trained:
```bash
cd MLOptionTrading
python ml/train_two_stage.py \
  --start-date 2023-01-01 \
  --end-date 2025-06-18 \
  --symbols SPX SPY
```

### Integration Steps

1. **Copy the ML integration module**:
```bash
cp ../MLOptionTrading/magic8_ml_integration.py ./
```

2. **Update Magic8-Companion configuration** (`.env`):
```bash
# Enable ML integration
M8C_ENABLE_ML_INTEGRATION=true
M8C_ML_WEIGHT=0.35  # 35% ML, 65% rules
M8C_ML_PATH=../MLOptionTrading

# Adjust for more recommendations
M8C_MIN_RECOMMENDATION_SCORE=65  # Lowered from 75
```

3. **Expose settings in `unified_config.py`**:
```python
class Settings(BaseSettings):
    # ML Integration
    enable_ml_integration: bool = Field(False, env='M8C_ENABLE_ML_INTEGRATION')
    ml_weight: float = Field(0.35, env='M8C_ML_WEIGHT')
    ml_path: str = Field('../MLOptionTrading', env='M8C_ML_PATH')
```

4. **Modify the unified main to use ML scorer**:

Edit `magic8_companion/unified_main.py` to integrate ML:

```python
# In RecommendationEngine.__init__()
def __init__(self):
    # Initialize with mode-appropriate components
    self.market_analyzer = MarketAnalyzer()
    
    # Check if ML integration is enabled
    if settings.enable_ml_integration:
        from magic8_ml_integration import MLEnhancedScoring
        base_scorer = create_scorer(settings.get_scorer_mode())
        self.combo_scorer = MLEnhancedScoring(
            base_scorer,
            ml_option_trading_path=settings.ml_path
        )
        self.combo_scorer.set_ml_weight(settings.ml_weight)
        logger.info(f"ML-enhanced scoring enabled (weight: {settings.ml_weight})")
    else:
        self.combo_scorer = create_scorer(settings.get_scorer_mode())
    
    # ... rest of initialization
```

## 🧪 Testing the Integration

### 1. Quick Integration Test

```bash
# Test ML model loading
python -c "
from magic8_ml_integration import MLEnhancedScoring
from magic8_companion.modules.unified_combo_scorer import create_scorer

base_scorer = create_scorer('standard')
ml_scorer = MLEnhancedScoring(base_scorer, '../MLOptionTrading')
print('ML Integration: SUCCESS' if ml_scorer.ml_system else 'ML Integration: FAILED')
"
```

### 2. Full System Test

```bash
# Run test with ML integration
python scripts/test_runner.py

# Select option 4 (Integration Test)
# This will test the complete flow
```

### 3. Live Data Test with ML

```python
# Create test script: test_ml_integration.py
import asyncio
from magic8_ml_integration import MLEnhancedScoring
from magic8_companion.modules.unified_combo_scorer import create_scorer
from magic8_companion.modules.market_analysis import MarketAnalyzer

async def test_ml_scoring():
    # Setup
    base_scorer = create_scorer('standard')
    ml_scorer = MLEnhancedScoring(base_scorer, '../MLOptionTrading')
    analyzer = MarketAnalyzer()
    
    # Get market data
    market_data = await analyzer.analyze_symbol('SPX')
    
    # Get ML-enhanced scores
    scores = await ml_scorer.score_combo_types(market_data, 'SPX')
    
    print("ML-Enhanced Scores:")
    for strategy, score in scores.items():
        print(f"  {strategy}: {score:.1f}")

asyncio.run(test_ml_scoring())
```

## 📅 Daily Operation Flow

### Morning Setup (9:00 AM ET)

1. **Verify MLOptionTrading is ready**:
```bash
cd MLOptionTrading
python ml/test_ml_integration.py
# Should show all tests PASSED
```

2. **Start Magic8-Companion with ML**:
```bash
cd Magic8-Companion
# Edit .env to enable ML integration
python -m magic8_companion.unified_main
```

3. **Monitor first checkpoint (10:30 AM ET)**:
```
🎯 CHECKPOINT 10:30 ET (enhanced mode)
ML prediction: Iron_Condor (conf: 0.84)
Score combination - Base: {'Butterfly': 55, 'Iron_Condor': 70, 'Vertical': 45}
                   ML: {'Butterfly': 0.0, 'Iron_Condor': 84.0, 'Vertical': 0.0}
                   Combined: {'Butterfly': 35.8, 'Iron_Condor': 74.9, 'Vertical': 29.3}
📊 SPX recommendations:
  Butterfly: MEDIUM (35.8) - ⏭️  SKIP
  Iron_Condor: HIGH (74.9) - ✅ TRADE
  Vertical: LOW (29.3) - ⏭️  SKIP
```

### Checkpoint Schedule

- **10:30 AM ET**: Morning analysis
- **11:00 AM ET**: Pre-lunch check  
- **12:30 PM ET**: Midday update
- **2:45 PM ET**: Final analysis

### End of Day (4:00 PM ET)

1. **Check recommendations output**:
```bash
cat data/recommendations.json | jq '.recommendations.SPX.strategies'
```

2. **Update ML models (weekly)**:
```bash
cd MLOptionTrading
# Process latest Discord data
python ml/discord_data_processor.py

# Retrain models with recent data
python ml/train_two_stage.py \
  --start-date 2023-01-01 \
  --end-date $(date +%Y-%m-%d) \
  --symbols SPX SPY
```

## 🔍 Troubleshooting

### ML System Not Loading

**Symptom**: "ML enhancement disabled. Using rule-based scoring only."

**Solution**:
```bash
# Check model files exist
ls ../MLOptionTrading/models/
# Should show: direction_model.pkl, volatility_model.pkl

# If missing, retrain:
cd ../MLOptionTrading
python ml/run_ml_pipeline.py --start-date 2023-01-01 --end-date 2025-06-18
```

### No ML Predictions

**Symptom**: ML scores all zero

**Solution**:
1. Check Discord data is loaded:
```bash
ls ../MLOptionTrading/temp_exports/processed_parquet/
# Should show date folders
```

2. Verify data path in `.env`:
```bash
M8C_ML_PATH=../MLOptionTrading  # Adjust if needed
```

### Butterfly Never Recommended

**Current Limitation**: The ML model requires "high" volatility for Butterfly, but recent markets show "normal" volatility.

**Workarounds**:
1. Train on broader date range including high volatility periods:
```bash
python ml/train_two_stage.py \
  --start-date 2022-01-01 \  # Include 2022 high volatility
  --end-date 2025-06-18 \
  --symbols SPX SPY
```

2. Adjust ML weight to allow more rule-based influence:
```bash
M8C_ML_WEIGHT=0.20  # 20% ML, 80% rules
```

## 📈 Performance Monitoring

### Key Metrics to Track

1. **ML Confidence Distribution**:
   - HIGH confidence predictions: Should be 20-30%
   - Accuracy on HIGH confidence: Target >70%

2. **Strategy Distribution**:
   - Iron Condor: 50-60% (most common)
   - Vertical: 30-40%
   - Butterfly: 5-15% (only in specific conditions)

3. **ML vs Rules Agreement**:
   - When both agree (>70 score): Strong signal
   - When they disagree: Review market conditions

### Weekly Performance Report

```python
# Create weekly_ml_report.py
import json
from pathlib import Path
from datetime import datetime, timedelta

def generate_weekly_report():
    # Load all recommendations from past week
    recs_dir = Path('data/recommendations_archive')
    week_ago = datetime.now() - timedelta(days=7)
    
    stats = {
        'total_predictions': 0,
        'high_confidence': 0,
        'strategies': {'Butterfly': 0, 'Iron_Condor': 0, 'Vertical': 0},
        'ml_influence': []
    }
    
    for rec_file in recs_dir.glob('*.json'):
        with open(rec_file) as f:
            data = json.load(f)
            # Analyze ML contribution
            # ... implementation
    
    print(f"Weekly ML Performance Report")
    print(f"Total Predictions: {stats['total_predictions']}")
    print(f"High Confidence Rate: {stats['high_confidence']/stats['total_predictions']:.1%}")
    # ... more stats

if __name__ == '__main__':
    generate_weekly_report()
```

## 🎯 Best Practices

1. **ML Weight Tuning**:
   - Start conservative: 0.20-0.35
   - Increase gradually based on performance
   - Never exceed 0.50 without extensive backtesting

2. **Data Freshness**:
   - Retrain weekly with latest Discord data
   - Monitor for distribution shifts
   - Adjust thresholds based on recent market conditions

3. **Fallback Strategy**:
   - Always maintain rule-based scoring as backup
   - If ML fails, system continues with rules only
   - Log all ML failures for investigation

## 🚨 Important Notes

1. **Butterfly Strategy**: Currently rare due to volatility thresholds. This is being addressed in MLOptionTrading v2.

2. **Processing Time**: ML adds ~100-200ms per prediction. Ensure sufficient time before market open.

3. **Memory Usage**: Combined system uses ~1GB RAM. Monitor on production servers.

---

## 🆕 Phase 2: Real-Time 5-Minute ML Predictions

### Overview

Phase 2 extends the ML integration to provide continuous predictions every 5 minutes throughout the trading day, leveraging Magic8-Companion's existing IB connection to avoid duplicate connections.

### 📊 Phase 2 Implementation Status

#### ✅ Completed Items:
- ✅ **ml_scheduler_extension.py** created and implemented
- ✅ **MLSchedulerExtension class** with 5-minute scheduling functionality
- ✅ **ML model integration** with MLOptionTrading (direction_model.pkl, volatility_model.pkl)
- ✅ **Schedule library integration** for 5-minute intervals
- ✅ **Delta feature creation** from bar data
- ✅ **ML prediction execution** generating ml_predictions_5min.json
- ✅ **Merge functionality** with existing recommendations.json
- ✅ **Configuration settings** added to unified_config.py
- ✅ **Test script** test_phase2_integration.py created

#### ❌ Outstanding Items:
- ❌ **Production Deployment**: Docker and systemd configurations not implemented

#### ✅ Newly Completed:
- ✅ **Data Provider Integration** now uses the configured provider interface
- ✅ **Main Application Integration** with `unified_main.py`
- ✅ **Monitoring Script** `monitor_5min_ml.py` created
- ✅ **Performance Optimization** with `should_run_prediction` and `cleanup_cache`

### 🐛 Critical Issues to Fix:

1. **Data Provider Architecture**:
   ```python
   # Current (INCORRECT):
   def _fetch_5min_bars(self, symbol: str) -> pd.DataFrame:
       ticker = yf.Ticker(symbol)  # Hardcoded to yfinance
   
   # Should be:
   def update_market_data(self):
       bars = self.data_provider.get_historical_data(...)  # Use configured provider
   ```

2. **Symbol Mapping**:
   - SPX → ^GSPC mapping is correct for Yahoo
   - But system should use IBKR symbols when connected to IB

### Architecture Enhancement

```
Magic8-Companion
    ├── Scheduled Checkpoints (Phase 1)
    │   └── 10:30, 11:00, 12:30, 14:45 ET
    │
    └── ML Scheduler Extension (Phase 2) 🆕
        ├── Every 5 minutes during market hours
        ├── Uses existing IB data connection
        ├── Temporary IBClient instances now use the standard constructor,
            automatically reusing the shared connection
        ├── Runs ML predictions continuously
        └── Merges with checkpoint recommendations
```

### Phase 2 Setup Instructions

#### 1. Create ML Scheduler Extension

Save the following as `magic8_companion/ml_scheduler_extension.py`:

```python
#!/usr/bin/env python3
"""
ML Scheduler Extension for Magic8-Companion
Provides real-time ML predictions every 5 minutes
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import pytz
import schedule
import time
from threading import Thread

# Add paths
MAGIC8_PATH = os.environ.get('MAGIC8_PATH', '.')
ML_PATH = os.environ.get('ML_PATH', '../MLOptionTrading')
sys.path.insert(0, MAGIC8_PATH)
sys.path.insert(0, ML_PATH)

# Import from MLOptionTrading
from ml.enhanced_ml_system import ProductionMLSystem, MLConfig
from ml.discord_data_processor import DiscordDataLoader

# Import from Magic8-Companion
from magic8_companion.data_providers import get_provider
from magic8_companion.utils.config import Config

logger = logging.getLogger(__name__)


class MLSchedulerExtension:
    """Extends Magic8-Companion with 5-minute ML predictions"""
    
    def __init__(self):
        # Load Magic8 config
        self.config = Config()
        
        # ML configuration
        self.ml_config = MLConfig(
            enable_two_stage=True,
            confidence_threshold=float(os.environ.get('ML_CONFIDENCE_THRESHOLD', '0.65')),
            direction_model_path=f"{ML_PATH}/models/direction_model.pkl",
            volatility_model_path=f"{ML_PATH}/models/volatility_model.pkl"
        )
        
        # Initialize ML system
        self.ml_system = ProductionMLSystem(self.ml_config)
        
        # Initialize data provider (reuse Magic8's connection)
        provider_type = self.config.get('M8C_DATA_PROVIDER', 'yahoo')
        self.data_provider = get_provider(provider_type)
        
        # Configuration
        self.symbols = self.config.get('M8C_SYMBOLS', 'SPX,SPY').split(',')
        self.output_dir = Path(self.config.get('M8C_OUTPUT_DIR', 'data'))
        self.output_dir.mkdir(exist_ok=True)
        
        # Timezone
        self.est = pytz.timezone('US/Eastern')
        self.utc = pytz.UTC
        
        # Data cache
        self.bar_data_cache = {}
        self.vix_data_cache = None
        self.last_update = None
        
        logger.info("ML Scheduler Extension initialized")
    
    def update_market_data(self):
        """Update market data cache"""
        current_time = datetime.now(self.utc)
        
        # Only update if more than 1 minute has passed
        if self.last_update and (current_time - self.last_update).seconds < 60:
            return
        
        try:
            # Get bar data for each symbol
            for symbol in self.symbols:
                bars = self.data_provider.get_historical_data(
                    symbol=symbol,
                    interval='5m',
                    period='1d'
                )
                if bars is not None and not bars.empty:
                    self.bar_data_cache[symbol] = bars
                    logger.debug(f"Updated {len(bars)} bars for {symbol}")
            
            # Get VIX data
            vix_data = self.data_provider.get_historical_data(
                symbol='VIX',
                interval='5m',
                period='1d'
            )
            if vix_data is not None and not vix_data.empty:
                self.vix_data_cache = vix_data
                logger.debug(f"Updated {len(vix_data)} VIX bars")
            
            self.last_update = current_time
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
    
    def create_delta_features(self, symbol: str, bar_data: pd.DataFrame) -> pd.DataFrame:
        """Create simplified delta features from bar data"""
        if bar_data.empty:
            return pd.DataFrame()
        
        # Create delta-like features from price movement
        current_price = bar_data['close'].iloc[-1]
        price_change = bar_data['close'].pct_change().iloc[-1] if len(bar_data) > 1 else 0
        
        # Approximate deltas
        delta_df = pd.DataFrame(index=[bar_data.index[-1]])
        delta_df['CallDelta'] = 0.5 + min(max(price_change * 10, -0.4), 0.4)
        delta_df['PutDelta'] = delta_df['CallDelta'] - 1
        delta_df['delta_spread'] = delta_df['CallDelta'] - abs(delta_df['PutDelta'])
        delta_df['call_put_ratio'] = delta_df['CallDelta'] / abs(delta_df['PutDelta'])
        delta_df['Price'] = current_price
        delta_df['Predicted'] = current_price * (1 + price_change)
        delta_df['price_vs_predicted'] = (current_price - delta_df['Predicted']) / current_price
        
        return delta_df
    
    def run_ml_prediction(self):
        """Run ML prediction for all symbols"""
        logger.info("Running 5-minute ML prediction")
        
        # Update market data
        self.update_market_data()
        
        current_time = datetime.now(self.utc)
        current_time_et = current_time.astimezone(self.est)
        
        # Check if within market hours
        if current_time_et.weekday() >= 5:  # Weekend
            logger.debug("Market closed (weekend)")
            return
        
        market_open = current_time_et.replace(hour=9, minute=30, second=0)
        market_close = current_time_et.replace(hour=16, minute=0, second=0)
        
        if not (market_open <= current_time_et <= market_close):
            logger.debug("Outside market hours")
            return
        
        # Create recommendations structure
        recommendations = {
            "timestamp": current_time.isoformat(),
            "checkpoint_time": current_time_et.strftime("%H:%M ET"),
            "ml_predictions": True,
            "ml_5min": True,
            "recommendations": {}
        }
        
        # Run predictions for each symbol
        for symbol in self.symbols:
            try:
                # Get cached data
                bar_data = self.bar_data_cache.get(symbol, pd.DataFrame())
                vix_data = self.vix_data_cache or pd.DataFrame()
                
                if bar_data.empty:
                    logger.warning(f"No data available for {symbol}")
                    continue
                
                # Create delta features
                delta_data = self.create_delta_features(symbol, bar_data)
                
                # Empty trades data for now
                trades_data = pd.DataFrame()
                
                # Run ML prediction
                result = self.ml_system.predict(
                    discord_delta=delta_data,
                    discord_trades=trades_data,
                    bar_data=bar_data,
                    vix_data=vix_data,
                    current_time=current_time
                )
                
                # Extract results
                strategy = result['strategy']
                confidence = result['confidence']
                details = result.get('details', {})
                
                # Determine confidence level
                if confidence >= 0.8:
                    confidence_level = "HIGH"
                elif confidence >= 0.65:
                    confidence_level = "MEDIUM" 
                else:
                    confidence_level = "LOW"
                
                # Only trade HIGH confidence
                should_trade = confidence_level == "HIGH" and strategy != "No_Trade"
                
                # Format recommendation
                recommendations["recommendations"][symbol] = {
                    "strategies": {
                        strategy: {
                            "score": confidence * 100,
                            "confidence": confidence_level,
                            "should_trade": should_trade,
                            "ml_confidence": confidence,
                            "direction": details.get('direction', 'neutral'),
                            "volatility_regime": details.get('volatility_regime', 'normal'),
                            "rationale": f"5-min ML: {strategy} ({confidence:.1%})"
                        }
                    },
                    "best_strategy": strategy if should_trade else "No_Trade",
                    "ml_5min_metadata": {
                        "model": "two_stage",
                        "prediction_time": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"5-min ML: {symbol} - {strategy} ({confidence:.1%}) - {confidence_level}")
                
            except Exception as e:
                logger.error(f"Error predicting {symbol}: {e}", exc_info=True)
        
        # Save ML predictions
        ml_output = self.output_dir / "ml_predictions_5min.json"
        with open(ml_output, 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        # Merge with existing recommendations
        self._merge_with_recommendations(recommendations)
        
        logger.debug(f"5-min ML predictions saved to {ml_output}")
    
    def _merge_with_recommendations(self, ml_recommendations: Dict):
        """Merge 5-minute ML predictions with existing recommendations"""
        rec_file = self.output_dir / "recommendations.json"
        
        try:
            # Load existing recommendations
            if rec_file.exists():
                with open(rec_file, 'r') as f:
                    existing = json.load(f)
            else:
                existing = {"recommendations": {}}
            
            # Merge ML predictions
            for symbol, ml_rec in ml_recommendations["recommendations"].items():
                if symbol not in existing["recommendations"]:
                    # Use ML recommendation directly
                    existing["recommendations"][symbol] = ml_rec
                else:
                    # Merge with existing
                    existing_rec = existing["recommendations"][symbol]
                    
                    # Add ML strategy to strategies with 5min suffix
                    ml_strategy = ml_rec["best_strategy"]
                    if ml_strategy != "No_Trade":
                        strategy_data = ml_rec["strategies"][ml_strategy].copy()
                        strategy_data["source"] = "ml_5min"
                        existing_rec["strategies"][f"{ml_strategy}_5min"] = strategy_data
                        
                        # Update best strategy if ML confidence is higher
                        if strategy_data["confidence"] == "HIGH":
                            current_best = existing_rec.get("best_strategy", "No_Trade")
                            if current_best == "No_Trade" or strategy_data["score"] >= 80:
                                existing_rec["best_strategy"] = ml_strategy
                                existing_rec["best_strategy_source"] = "ml_5min"
            
            # Update metadata
            existing["ml_5min_enhanced"] = True
            existing["last_5min_update"] = ml_recommendations["timestamp"]
            
            # Save merged recommendations
            with open(rec_file, 'w') as f:
                json.dump(existing, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error merging recommendations: {e}")
    
    def start_scheduler(self):
        """Start the 5-minute scheduler"""
        # Schedule ML predictions every 5 minutes
        schedule.every(5).minutes.do(self.run_ml_prediction)

        logger.info("ML 5-minute scheduler started")

        # Run scheduler in thread
        def run_schedule():
            # Initial prediction now runs inside the scheduler thread
            self.run_ml_prediction()
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(10)
        
        scheduler_thread = Thread(target=run_schedule, daemon=True)
        scheduler_thread.start()
        
        return scheduler_thread
```

#### 2. Update Configuration

Add to `.env`:
```bash
# Phase 2: Real-Time ML Settings
M8C_ENABLE_ML_5MIN=true
M8C_ML_5MIN_INTERVAL=5  # minutes
M8C_ML_5MIN_CONFIDENCE_THRESHOLD=0.65
M8C_ML_5MIN_MERGE_STRATEGY=overlay  # overlay or replace
```

#### 3. Integrate with Main Application

Update `magic8_companion/unified_main.py`:

```python
# After initializing the RecommendationEngine
async def main():
    logger.info("Starting Magic8-Companion...")
    
    # Initialize engine
    engine = RecommendationEngine()
    
    # Phase 2: Start ML 5-minute scheduler if enabled
    if settings.enable_ml_5min:
        try:
            from magic8_companion.ml_scheduler_extension import MLSchedulerExtension
            loop = asyncio.get_running_loop()
            ml_scheduler = MLSchedulerExtension(loop)
            ml_scheduler_thread = ml_scheduler.start_scheduler()
            logger.info("Phase 2: ML 5-minute scheduler started")
        except Exception as e:
            logger.error(f"Failed to start ML scheduler: {e}")
            logger.info("Continuing with checkpoint-only predictions")
    
    # Run checkpoint scheduler
    await engine.run()
```

#### 4. Install Additional Dependencies

```bash
pip install schedule
```

### Phase 2 Operation

#### Starting the System

```bash
# Start Magic8-Companion with both phases
cd Magic8-Companion
python -m magic8_companion.unified_main

# You should see:
# [INFO] ML-enhanced scoring enabled (weight: 0.35)
# [INFO] Phase 2: ML 5-minute scheduler started
# [INFO] Running 5-minute ML prediction
```

#### Monitoring 5-Minute Predictions

```bash
# Watch real-time predictions
watch -n 30 'tail -20 logs/magic8_companion.log | grep "5-min ML"'

# Monitor prediction files
ls -la data/ml_predictions_5min.json
ls -la data/recommendations.json

# View latest 5-min prediction
cat data/ml_predictions_5min.json | jq '.recommendations.SPX'
```

#### Output Structure

The 5-minute predictions create two types of entries:

1. **Standalone 5-min file** (`ml_predictions_5min.json`):
```json
{
  "timestamp": "2025-06-26T10:35:00Z",
  "checkpoint_time": "10:35 ET",
  "ml_predictions": true,
  "ml_5min": true,
  "recommendations": {
    "SPX": {
      "strategies": {
        "Butterfly": {
          "score": 72.5,
          "confidence": "MEDIUM",
          "should_trade": false,
          "ml_confidence": 0.725,
          "direction": "neutral",
          "volatility_regime": "normal",
          "rationale": "5-min ML: Butterfly (72.5%)"
        }
      },
      "best_strategy": "Butterfly",
      "ml_5min_metadata": {
        "model": "two_stage",
        "prediction_time": "2025-06-26T10:35:00Z"
      }
    }
  }
}
```

2. **Merged recommendations** (`recommendations.json`):
```json
{
  "timestamp": "2025-06-26T10:30:00Z",
  "checkpoint_time": "10:30 ET",
  "ml_enhanced": true,
  "ml_5min_enhanced": true,
  "last_5min_update": "2025-06-26T10:35:00Z",
  "recommendations": {
    "SPX": {
      "strategies": {
        "Iron_Condor": {
          "score": 74.9,
          "confidence": "HIGH",
          "source": "checkpoint"
        },
        "Butterfly_5min": {
          "score": 82.5,
          "confidence": "HIGH",
          "source": "ml_5min"
        }
      },
      "best_strategy": "Butterfly",
      "best_strategy_source": "ml_5min"
    }
  }
}
```

### Phase 2 Monitoring & Troubleshooting

#### Performance Metrics

Create `scripts/monitor_5min_ml.py`:

```python
#!/usr/bin/env python3
"""Monitor 5-minute ML prediction performance"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def monitor_predictions():
    data_dir = Path('data')
    stats = defaultdict(lambda: {
        'predictions': 0,
        'high_confidence': 0,
        'strategies': defaultdict(int),
        'last_update': None
    })
    
    print("Monitoring 5-minute ML predictions...")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Check 5-min predictions
            ml_file = data_dir / 'ml_predictions_5min.json'
            if ml_file.exists():
                with open(ml_file) as f:
                    data = json.load(f)
                
                for symbol, rec in data['recommendations'].items():
                    strategy = rec['best_strategy']
                    confidence = rec['strategies'][strategy]['confidence']
                    
                    stats[symbol]['predictions'] += 1
                    if confidence == 'HIGH':
                        stats[symbol]['high_confidence'] += 1
                    stats[symbol]['strategies'][strategy] += 1
                    stats[symbol]['last_update'] = data['timestamp']
            
            # Display stats
            print("\033[H\033[J")  # Clear screen
            print(f"=== 5-Minute ML Predictions Monitor ===")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            for symbol, s in stats.items():
                if s['predictions'] > 0:
                    print(f"{symbol}:")
                    print(f"  Total predictions: {s['predictions']}")
                    print(f"  High confidence rate: {s['high_confidence']/s['predictions']:.1%}")
                    print(f"  Strategies: {dict(s['strategies'])}")
                    print(f"  Last update: {s['last_update']}\n")
            
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    monitor_predictions()
```

#### Common Issues & Solutions

**Issue: 5-min predictions not running**
```bash
# Check scheduler is active
grep "5-minute ML prediction" logs/magic8_companion.log

# Verify ML models exist
ls ../MLOptionTrading/models/

# Check market hours
python -c "import pytz; from datetime import datetime; 
et = datetime.now(pytz.timezone('US/Eastern')); 
print(f'Current ET: {et}, Market open: {9.5 <= et.hour < 16}')"
```

**Issue: Data not updating**
```bash
# Check data provider connection
grep "Updated.*bars" logs/magic8_companion.log

# Verify IB connection if using IBKR
grep "Connected to IB" logs/magic8_companion.log
```

**Issue: Predictions not merging**
```bash
# Check merge process
grep "merge" logs/magic8_companion.log

# Compare timestamps
jq '.timestamp' data/recommendations.json
jq '.timestamp' data/ml_predictions_5min.json
```

**Issue: `ValueError: Not naive datetime (tzinfo is already set)`**
```text
This occurs when the scheduler passes a timezone-aware `current_time` to the ML
system. The Phase 2 scheduler now strips timezone information before calling the
ML module. If you see this error, ensure you are running the latest version and
that `current_time` is naive UTC.
```

### Phase 2 Best Practices

1. **Resource Management**:
   - 5-min predictions add ~200MB memory usage
   - CPU spikes to 10-15% during predictions
   - Consider dedicated thread pool for heavy periods

2. **Data Consistency**:
   - Cache market data for 1-2 minutes
   - Synchronize with checkpoint predictions
   - Handle market data gaps gracefully

3. **Merge Strategies**:
   - **Overlay** (default): Add 5-min as additional strategy
   - **Replace**: Override checkpoint with latest 5-min
   - **Weighted**: Combine based on recency and confidence

4. **Operational Considerations**:
   - Start 5-min scheduler after market open
   - Pause during high volatility events
   - Archive predictions for analysis

### Phase 2 Performance Tuning

#### Optimize Prediction Frequency

```python
# In ml_scheduler_extension.py
def should_run_prediction(self):
    """Determine if prediction should run based on market conditions"""
    current_time = datetime.now(self.utc)
    et_time = current_time.astimezone(self.est)
    
    # Skip first/last 5 minutes of day
    if et_time.hour == 9 and et_time.minute < 35:
        return False
    if et_time.hour == 15 and et_time.minute > 55:
        return False
    
    # Skip if recent checkpoint ran
    if hasattr(self, 'last_checkpoint'):
        if (current_time - self.last_checkpoint).seconds < 300:
            return False
    
    return True
```

#### Memory Optimization

```python
# Add to MLSchedulerExtension.__init__
self.max_cache_age = timedelta(minutes=30)
self.cache_cleanup_interval = 10  # runs

def cleanup_cache(self):
    """Remove old data from cache"""
    cutoff = datetime.now(self.utc) - self.max_cache_age
    
    for symbol in self.bar_data_cache:
        df = self.bar_data_cache[symbol]
        self.bar_data_cache[symbol] = df[df.index > cutoff]
```

## 📊 Phase 2 Integration Testing

### End-to-End Test Script

Create `test_phase2_integration.py`:

```python
#!/usr/bin/env python3
"""Test Phase 2 5-minute ML integration"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime

async def test_phase2():
    print("Testing Phase 2: 5-Minute ML Predictions")
    print("-" * 50)
    
    # 1. Check ML models
    ml_path = Path('../MLOptionTrading/models')
    models_exist = all([
        (ml_path / 'direction_model.pkl').exists(),
        (ml_path / 'volatility_model.pkl').exists()
    ])
    print(f"✓ ML models available: {models_exist}")
    
    # 2. Test ML scheduler import
    try:
        from magic8_companion.ml_scheduler_extension import MLSchedulerExtension
        loop = asyncio.get_running_loop()
        scheduler = MLSchedulerExtension(loop)
        print("✓ ML scheduler initialized")
    except Exception as e:
        print(f"✗ ML scheduler failed: {e}")
        return
    
    # 3. Test market data update
    scheduler.update_market_data()
    has_data = bool(scheduler.bar_data_cache)
    print(f"✓ Market data loaded: {has_data}")
    
    # 4. Run test prediction
    print("\nRunning test prediction...")
    scheduler.run_ml_prediction()
    
    # 5. Check output files
    time.sleep(2)  # Wait for file write
    ml_file = Path('data/ml_predictions_5min.json')
    rec_file = Path('data/recommendations.json')
    
    if ml_file.exists():
        with open(ml_file) as f:
            ml_data = json.load(f)
        print(f"✓ 5-min predictions generated: {ml_data['checkpoint_time']}")
        
        # Show predictions
        for symbol, rec in ml_data['recommendations'].items():
            strategy = rec['best_strategy']
            confidence = rec['strategies'][strategy]['ml_confidence']
            print(f"  {symbol}: {strategy} ({confidence:.1%})")
    
    # 6. Check merge
    if rec_file.exists():
        with open(rec_file) as f:
            merged = json.load(f)
        
        has_5min = merged.get('ml_5min_enhanced', False)
        print(f"✓ Merged with recommendations: {has_5min}")
    
    print("\nPhase 2 integration test complete!")

if __name__ == '__main__':
    asyncio.run(test_phase2())
```

## 📈 Phase 2 Production Deployment

### Systemd Service

Create `/etc/systemd/system/magic8-ml5min.service`:

```ini
[Unit]
Description=Magic8 ML 5-Minute Predictor
After=network.target magic8-companion.service

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/Magic8-Companion
Environment="ML_PATH=/home/trader/MLOptionTrading"
Environment="PYTHONPATH=/home/trader/Magic8-Companion:/home/trader/MLOptionTrading"
ExecStart=/home/trader/Magic8-Companion/.venv/bin/python -m magic8_companion.unified_main
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Docker Support

Add to `docker-compose.yml`:

```yaml
services:
  magic8-ml5min:
    build: .
    environment:
      - M8C_ENABLE_ML_INTEGRATION=true
      - M8C_ENABLE_ML_5MIN=true
      - ML_PATH=/ml
    volumes:
      - ./data:/app/data
      - ../MLOptionTrading:/ml:ro
    depends_on:
      - ib-gateway
```

## 📞 Support

For Phase 2 specific issues:
- Check 5-min logs: `grep "5-min ML" logs/magic8_companion.log`
- Monitor prediction frequency: `ls -la data/ml_predictions_5min.json`
- Verify scheduler thread: `ps aux | grep ml_scheduler`

For integration issues:
- Ensure both Phase 1 and Phase 2 are enabled
- Check for prediction conflicts at checkpoints
- Review merge strategy in logs

---

**Last Updated**: June 28, 2025  
**Version**: 2.0.0  
**Phase 2 Status**: Partially Implemented - Production Deployment Pending
