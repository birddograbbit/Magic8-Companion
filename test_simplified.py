#!/usr/bin/env python3
"""
Test script for simplified Magic8-Companion.
Tests the recommendation engine without waiting for scheduled checkpoints.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from magic8_companion.main_simplified import RecommendationEngine
from magic8_companion.config_simplified import settings

async def test_recommendation_engine():
    """Test the recommendation engine."""
    print("🧪 Testing Magic8-Companion Recommendation Engine")
    print("=" * 50)
    
    # Create recommendation engine
    engine = RecommendationEngine()
    
    # Generate recommendations
    print("Generating recommendations...")
    recommendations = await engine.generate_recommendations()
    
    # Display results
    print(f"\n📊 Results for {recommendations['checkpoint_time']}:")
    print(f"Timestamp: {recommendations['timestamp']}")
    
    if recommendations.get("recommendations"):
        for symbol, rec in recommendations["recommendations"].items():
            print(f"\n{symbol}:")
            print(f"  Preferred Strategy: {rec['preferred_strategy']}")
            print(f"  Score: {rec['score']}")
            print(f"  Confidence: {rec['confidence']}")
            print(f"  Rationale: {rec['rationale']}")
            print(f"  All Scores: {rec['all_scores']}")
    else:
        print("  No recommendations generated (scores below threshold)")
    
    # Save recommendations
    await engine.save_recommendations(recommendations)
    print(f"\n💾 Recommendations saved to: {settings.output_file_path}")
    
    # Show file contents
    output_file = Path(settings.output_file_path)
    if output_file.exists():
        print(f"\n📄 File contents:")
        with open(output_file, 'r') as f:
            content = json.load(f)
            print(json.dumps(content, indent=2))

async def test_individual_symbol():
    """Test recommendation for a single symbol."""
    print("\n🔍 Testing individual symbol analysis:")
    print("=" * 50)
    
    engine = RecommendationEngine()
    symbol = "SPX"
    
    # Test market analysis
    market_data = await engine.market_analyzer.analyze_symbol(symbol)
    print(f"\n{symbol} Market Data:")
    print(json.dumps(market_data, indent=2))
    
    # Test combo scoring
    scores = engine.combo_scorer.score_combo_types(market_data, symbol)
    print(f"\n{symbol} Combo Scores:")
    for strategy, score in scores.items():
        print(f"  {strategy}: {score:.1f}")

if __name__ == "__main__":
    print("Starting Magic8-Companion Test Suite...")
    
    try:
        # Run tests
        asyncio.run(test_recommendation_engine())
        asyncio.run(test_individual_symbol())
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
