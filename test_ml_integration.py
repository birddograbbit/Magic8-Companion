#!/usr/bin/env python3
"""
Test script to verify ML integration is working correctly in Magic8-Companion
Run this from the Magic8-Companion directory
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_ml_integration():
    """Test ML integration with Magic8-Companion"""
    
    print("="*60)
    print("Testing ML Integration with Magic8-Companion")
    print("="*60)
    
    # Step 1: Check paths
    print("\n1. Checking paths...")
    current_dir = Path.cwd()
    print(f"   Current directory: {current_dir}")
    
    ml_path = Path("../MLOptionTrading").resolve()
    print(f"   MLOptionTrading path: {ml_path}")
    print(f"   MLOptionTrading exists: {ml_path.exists()}")
    
    models_dir = ml_path / "models"
    print(f"   Models directory: {models_dir}")
    print(f"   Models directory exists: {models_dir.exists()}")
    
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl"))
        print(f"   Found {len(model_files)} model files:")
        for f in model_files:
            print(f"      - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Step 2: Test import
    print("\n2. Testing ML integration import...")
    try:
        from magic8_ml_integration import MLEnhancedScoring
        print("   ✓ Successfully imported MLEnhancedScoring")
    except Exception as e:
        print(f"   ✗ Failed to import: {e}")
        return
    
    # Step 3: Create mock scorer
    print("\n3. Creating test scorer...")
    
    class MockScorer:
        async def score_combo_types(self, market_data, symbol):
            return {
                'Butterfly': 55,
                'Iron_Condor': 65,
                'Vertical': 45
            }
    
    base_scorer = MockScorer()
    
    # Step 4: Initialize ML enhanced scorer
    print("\n4. Initializing ML enhanced scorer...")
    try:
        enhanced_scorer = MLEnhancedScoring(base_scorer, ml_option_trading_path="../MLOptionTrading")
        print("   ✓ MLEnhancedScoring initialized")
        
        # Check if ML system loaded
        if enhanced_scorer.ml_system is not None:
            print("   ✓ ML system loaded successfully")
        else:
            print("   ✗ ML system NOT loaded - check logs above")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Test prediction
    print("\n5. Testing ML prediction...")
    
    # Create test market data
    market_data = {
        'price': 6088,
        'vix': 17.5,
        'volume': 1500000,
        'high': 6095,
        'low': 6080,
        'iv_percentile': 45,
        'expected_range_pct': 0.012
    }
    
    try:
        # Get enhanced scores
        scores = await enhanced_scorer.score_combo_types(market_data, 'SPX')
        
        print("\n   Results:")
        print(f"   Base scores: {await base_scorer.score_combo_types(market_data, 'SPX')}")
        print(f"   Enhanced scores: {scores}")
        
        # Check if ML is actually working
        base_scores = await base_scorer.score_combo_types(market_data, 'SPX')
        ml_working = any(abs(scores[k] - base_scores[k]) > 0.1 for k in scores)
        
        if ml_working:
            print("\n   ✓ ML integration is working! Scores are being adjusted by ML predictions.")
        else:
            print("\n   ⚠️  ML scores are identical to base scores - ML may not be working properly")
            
    except Exception as e:
        print(f"\n   ✗ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 6: Diagnostic info
    print("\n6. Diagnostic Summary:")
    print("   " + "-"*40)
    
    if enhanced_scorer.ml_system is None:
        print("   ⚠️  ML system not loaded. Possible causes:")
        print("      1. Models not trained (run ML pipeline)")
        print("      2. Import errors (check MLOptionTrading installation)")
        print("      3. Path issues (verify ../MLOptionTrading path)")
    else:
        print("   ✓ ML system loaded and operational")
        print(f"   ML weight: {enhanced_scorer.ml_weight:.0%}")
    
    print("\n" + "="*60)
    print("Test complete!")
    
    # Return success status
    return enhanced_scorer.ml_system is not None


async def quick_ml_check():
    """Quick check to see if ML is returning predictions"""
    print("\n" + "="*60)
    print("Quick ML Module Check")
    print("="*60)
    
    # Add MLOptionTrading to path
    ml_path = Path("../MLOptionTrading").resolve()
    if str(ml_path) not in sys.path:
        sys.path.insert(0, str(ml_path))
    
    try:
        from ml.enhanced_ml_system import ProductionMLSystem, MLConfig
        
        # Create config with absolute paths
        models_dir = ml_path / "models"
        config = MLConfig(
            enable_two_stage=True,
            direction_model_path=str((models_dir / "direction_model.pkl").resolve()),
            volatility_model_path=str((models_dir / "volatility_model.pkl").resolve())
        )
        
        ml_system = ProductionMLSystem(config)
        
        # Create minimal test data
        current_time = datetime.now()
        
        bar_data = pd.DataFrame({
            'open': [6000],
            'high': [6010],
            'low': [5990],
            'close': [6005],
            'volume': [1000000]
        }, index=[current_time])
        
        vix_data = pd.DataFrame({
            'close': [17.5]
        }, index=[current_time])
        
        # Get prediction
        result = ml_system.predict(
            discord_delta=pd.DataFrame(),
            discord_trades=pd.DataFrame(),
            bar_data=bar_data,
            vix_data=vix_data,
            current_time=current_time
        )
        
        print(f"\nDirect ML prediction:")
        print(f"Strategy: {result['strategy']}")
        print(f"Confidence: {result['confidence']:.2%}")
        
        if result['confidence'] > 0:
            print("\n✓ ML models are working correctly!")
        else:
            print("\n✗ ML models returned 0 confidence - models may not be trained")
            
    except Exception as e:
        print(f"\n✗ Error testing ML directly: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run main test
    success = asyncio.run(test_ml_integration())
    
    # Run quick ML check
    asyncio.run(quick_ml_check())
    
    print("\n" + "="*60)
    if success:
        print("✨ ML integration test PASSED!")
    else:
        print("❌ ML integration test FAILED - see errors above")
