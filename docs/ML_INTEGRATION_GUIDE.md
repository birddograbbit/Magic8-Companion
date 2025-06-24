# ML Integration Guide: Magic8-Companion + MLOptionTrading

## 🚀 Overview

This guide details the complete integration between Magic8-Companion and MLOptionTrading, enabling ML-enhanced trading recommendations based on 2.5 years of profitable Discord trading history.

**Current System Status**: ✅ Production Test Ready

## 🏗️ Architecture

```
Discord Trading History (2022-2025) → MLOptionTrading (ML Training)
                                              ↓
                                    Two-Stage ML Models
                                    (Direction + Volatility)
                                              ↓
Magic8-Companion (Rule-Based Scoring) ← ML Enhanced Scoring
                                              ↓
                                    recommendations.json
                                              ↓
                                      DiscordTrading
```

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

3. **Modify the unified main to use ML scorer**:

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
        logger.info("ML-enhanced scoring enabled")
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

## 📞 Support

For ML-specific issues:
- Check MLOptionTrading logs: `tail -f logs/ml_system.log`
- Review feature importance: `open feature_importance.png`
- Validate data pipeline: `python ml/validate_data_pipeline.py`

For integration issues:
- Enable debug logging: `M8C_LOG_LEVEL=DEBUG`
- Check ML weight: Reduce if seeing extreme scores
- Verify paths: Both repos must be accessible

---

**Last Updated**: June 24, 2025
**Version**: 1.0.0
**Status**: Production Test Ready
