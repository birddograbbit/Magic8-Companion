# Quick ML Integration Implementation

This file shows the exact code changes needed to integrate ML into Magic8-Companion.

## 1. Update `.env` file

Add these lines to your `.env`:

```bash
# ML Integration Settings
M8C_ENABLE_ML_INTEGRATION=true
M8C_ML_WEIGHT=0.35
M8C_ML_PATH=../MLOptionTrading
```

## 2. Update `magic8_companion/unified_config.py`

Add these ML configuration fields:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # ML Integration
    enable_ml_integration: bool = Field(False, env='M8C_ENABLE_ML_INTEGRATION')
    ml_weight: float = Field(0.35, env='M8C_ML_WEIGHT')
    ml_path: str = Field('../MLOptionTrading', env='M8C_ML_PATH')
```

## 3. Update `magic8_companion/unified_main.py`

Replace the `RecommendationEngine.__init__` method:

```python
def __init__(self):
    # Initialize with mode-appropriate components
    self.market_analyzer = MarketAnalyzer()
    
    # Check if ML integration is enabled
    if hasattr(settings, 'enable_ml_integration') and settings.enable_ml_integration:
        try:
            # Import ML integration module
            import sys
            sys.path.insert(0, '.')  # Add current directory to path
            from magic8_ml_integration import MLEnhancedScoring
            
            # Create base scorer
            base_scorer = create_scorer(settings.get_scorer_mode())
            
            # Wrap with ML enhancement
            self.combo_scorer = MLEnhancedScoring(
                base_scorer, 
                ml_option_trading_path=settings.ml_path
            )
            
            # Set ML weight if configured
            if hasattr(settings, 'ml_weight'):
                self.combo_scorer.set_ml_weight(settings.ml_weight)
            
            logger.info(f"ML-enhanced scoring enabled (weight: {settings.ml_weight})")
        except Exception as e:
            logger.warning(f"Failed to initialize ML integration: {e}")
            logger.info("Falling back to rule-based scoring")
            self.combo_scorer = create_scorer(settings.get_scorer_mode())
    else:
        self.combo_scorer = create_scorer(settings.get_scorer_mode())
    
    self.output_file = Path(settings.output_file_path)
    self.supported_symbols = settings.supported_symbols
    
    logger.info(f"Initialized in {settings.system_complexity} mode")
    logger.info(f"Scorer mode: {settings.get_scorer_mode()}")
```

## 4. Test the Integration

Run this test script to verify ML is working:

```python
# test_ml_enabled.py
import asyncio
import sys
sys.path.append('.')

from magic8_companion.unified_config import settings
from magic8_companion.unified_main import RecommendationEngine

async def test():
    # Force enable ML for test
    settings.enable_ml_integration = True
    settings.ml_path = '../MLOptionTrading'
    
    # Create engine
    engine = RecommendationEngine()
    
    # Check if ML is loaded
    if hasattr(engine.combo_scorer, 'ml_system'):
        print("✅ ML Integration: ENABLED")
        print(f"   ML Weight: {engine.combo_scorer.ml_weight}")
        print(f"   ML Path: {settings.ml_path}")
    else:
        print("❌ ML Integration: DISABLED")

asyncio.run(test())
```

## 5. Full Command Sequence

```bash
# 1. Ensure MLOptionTrading is ready
cd ../MLOptionTrading
python ml/test_ml_integration.py

# 2. Copy integration module to Magic8-Companion
cd ../Magic8-Companion
cp ../MLOptionTrading/magic8_ml_integration.py ./

# 3. Update .env file (add ML settings)
echo "M8C_ENABLE_ML_INTEGRATION=true" >> .env
echo "M8C_ML_WEIGHT=0.35" >> .env
echo "M8C_ML_PATH=../MLOptionTrading" >> .env

# 4. Test ML is working
python test_ml_enabled.py

# 5. Run Magic8-Companion with ML
python -m magic8_companion.unified_main
```

## Expected Output

When ML is properly integrated, you should see:

```
2025-06-24 10:30:00 - magic8_companion.unified_main - INFO - ML-enhanced scoring enabled (weight: 0.35)
2025-06-24 10:30:00 - magic8_ml_integration - INFO - ML system loaded successfully
...
2025-06-24 10:30:15 - magic8_ml_integration - INFO - ML prediction: Iron_Condor (conf: 0.84)
2025-06-24 10:30:15 - magic8_ml_integration - INFO - Score combination - Base: {'Butterfly': 55, 'Iron_Condor': 70, 'Vertical': 45}, ML: {'Butterfly': 0.0, 'Iron_Condor': 84.0, 'Vertical': 0.0}, Combined: {'Butterfly': 35.8, 'Iron_Condor': 74.9, 'Vertical': 29.3}
```

## Troubleshooting

If ML doesn't load:
1. Check `../MLOptionTrading/models/` contains `.pkl` files
2. Verify `magic8_ml_integration.py` is in the Magic8-Companion root
3. Check logs for specific error messages
4. Try running with `M8C_LOG_LEVEL=DEBUG` for more details
