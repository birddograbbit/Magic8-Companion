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

    ml_path = Path('../MLOptionTrading/models')
    models_exist = all([
        (ml_path / 'direction_model.pkl').exists(),
        (ml_path / 'volatility_model.pkl').exists()
    ])
    print(f"\u2713 ML models available: {models_exist}")

    try:
        from magic8_companion.ml_scheduler_extension import MLSchedulerExtension
        scheduler = MLSchedulerExtension()
        print("\u2713 ML scheduler initialized")
        print(f"Using provider: {scheduler.data_provider.__class__.__name__}")
    except Exception as e:
        print(f"\u2717 ML scheduler failed: {e}")
        return

    scheduler.update_market_data()
    has_data = bool(scheduler.bar_data_cache)
    print(f"\u2713 Market data loaded: {has_data}")

    print("\nRunning test prediction...")
    scheduler.run_ml_prediction()

    time.sleep(2)
    ml_file = Path('data/ml_predictions_5min.json')
    rec_file = Path('data/recommendations.json')

    if ml_file.exists():
        with open(ml_file) as f:
            ml_data = json.load(f)
        print(f"\u2713 5-min predictions generated: {ml_data['checkpoint_time']}")
        for symbol, rec in ml_data['recommendations'].items():
            strategy = rec['best_strategy']
            confidence = rec['strategies'][strategy]['ml_confidence']
            print(f"  {symbol}: {strategy} ({confidence:.1%})")

    if rec_file.exists():
        with open(rec_file) as f:
            merged = json.load(f)
        has_5min = merged.get('ml_5min_enhanced', False)
        print(f"\u2713 Merged with recommendations: {has_5min}")

    print("\nPhase 2 integration test complete!")

if __name__ == '__main__':
    asyncio.run(test_phase2())
