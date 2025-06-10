#!/usr/bin/env python3
"""
Quick test to run a checkpoint immediately for testing purposes
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from magic8_companion.main_simplified import RecommendationEngine


async def test_checkpoint():
    """Run a single checkpoint for testing"""
    print("Running test checkpoint...")
    
    engine = RecommendationEngine()
    
    # Generate recommendations
    recommendations = await engine.generate_recommendations()
    
    # Save to output file
    await engine.save_recommendations(recommendations)
    
    print("\nTest checkpoint complete!")
    print(f"Check the output at: {engine.output_file}")
    
    # Display summary
    if recommendations.get("recommendations"):
        print("\nGenerated recommendations:")
        for symbol, rec in recommendations["recommendations"].items():
            print(f"\n{symbol}:")
            for strategy, details in rec["strategies"].items():
                status = "✅ TRADE" if details["should_trade"] else "⏭️  SKIP"
                print(f"  {strategy}: {details['confidence']} (score: {details['score']}) - {status}")
    else:
        print("No recommendations generated")


if __name__ == "__main__":
    asyncio.run(test_checkpoint())
