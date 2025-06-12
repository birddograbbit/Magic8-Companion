#!/usr/bin/env python3
"""
Test script for Magic8-Companion with live market data.
Tests Yahoo Finance integration for real-time market analysis.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from magic8_companion.config import settings
from magic8_companion.modules.market_analysis import MarketAnalyzer
from magic8_companion.modules.combo_scorer import ComboScorer
from magic8_companion.main import RecommendationEngine
from magic8_companion.modules.ib_client_manager import IBClientManager


async def test_live_data_for_symbol(symbol: str):
    """Test live data fetching for a single symbol."""
    print(f"\n🔍 Testing live data for {symbol}:")
    print("=" * 50)
    
    # Override to use live data
    original_setting = settings.use_mock_data
    settings.use_mock_data = False
    
    try:
        analyzer = MarketAnalyzer()
        market_data = await analyzer.analyze_symbol(symbol)
        
        if market_data:
            print(json.dumps(market_data, indent=2))
            
            # Test combo scoring with live data
            scorer = ComboScorer()
            scores = scorer.score_combo_types(market_data, symbol)
            
            print(f"\n📊 Combo Scores for {symbol}:")
            for strategy, score in scores.items():
                print(f"  {strategy}: {score:.1f}")
        else:
            print("❌ Failed to fetch market data")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Restore original setting
        settings.use_mock_data = original_setting


async def test_live_recommendations():
    """Test full recommendation engine with live data."""
    print("\n🎯 Testing Full Recommendation Engine with Live Data:")
    print("=" * 50)
    
    # Override to use live data
    original_setting = settings.use_mock_data
    settings.use_mock_data = False
    settings.market_data_provider = "yahoo"
    
    try:
        engine = RecommendationEngine()
        recommendations = await engine.generate_recommendations()
        
        print(f"Timestamp: {recommendations['timestamp']}")
        print(f"Checkpoint: {recommendations['checkpoint_time']}")
        
        if recommendations.get("recommendations"):
            for symbol, rec in recommendations["recommendations"].items():
                print(f"\n{symbol}:")
                print(f"  Best Strategy: {rec['best_strategy']}")

                for strat, details in rec.get("strategies", {}).items():
                    print(f"  {strat}:")
                    print(f"    Score: {details['score']}")
                    print(f"    Confidence: {details['confidence']}")
                    print(f"    Should Trade: {details['should_trade']}")
                    if 'rationale' in details:
                        print(f"    Rationale: {details['rationale']}")

                if 'current_price' in rec.get('market_conditions', {}):
                    print(f"  Current Price: ${rec['market_conditions']['current_price']}")
                if 'implied_vol' in rec.get('market_conditions', {}):
                    print(f"  Implied Vol: {rec['market_conditions']['implied_vol']}%")
        else:
            print("No recommendations generated")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Restore original setting
        settings.use_mock_data = original_setting


async def compare_mock_vs_live():
    """Compare mock data with live data for validation."""
    print("\n📊 Comparing Mock vs Live Data:")
    print("=" * 50)
    
    analyzer = MarketAnalyzer()
    
    for symbol in ["SPX", "SPY"]:
        print(f"\n{symbol}:")
        
        # Get mock data
        settings.use_mock_data = True
        mock_data = await analyzer.analyze_symbol(symbol)
        
        # Get live data
        settings.use_mock_data = False
        try:
            live_data = await analyzer.analyze_symbol(symbol)
            
            print("  Mock IV: {:.1f}% | Live IV: {:.1f}%".format(
                mock_data['iv_percentile'],
                live_data['iv_percentile']
            ))
            print("  Mock Range: {:.2%} | Live Range: {:.2%}".format(
                mock_data['expected_range_pct'],
                live_data['expected_range_pct']
            ))
            
        except Exception as e:
            print(f"  Live data error: {e}")


async def cleanup_connections():
    """Clean up any open IB connections."""
    manager = IBClientManager()
    await manager.disconnect()
    # Small delay to ensure clean disconnection
    await asyncio.sleep(0.5)


def main():
    """Main test runner."""
    print("🚀 Magic8-Companion Live Data Testing")
    print("=" * 50)
    
    # Check market hours
    from datetime import datetime
    import pytz
    
    et_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(et_tz)
    print(f"Current ET time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Market hours check (9:30 AM - 4:00 PM ET on weekdays)
    if current_time.weekday() < 5:  # Monday = 0, Friday = 4
        market_open = current_time.replace(hour=9, minute=30, second=0)
        market_close = current_time.replace(hour=16, minute=0, second=0)
        
        if market_open <= current_time <= market_close:
            print("✅ Market is OPEN")
        else:
            print("⚠️  Market is CLOSED (outside regular hours)")
    else:
        print("⚠️  Market is CLOSED (weekend)")
    
    print("\nNote: Yahoo Finance data may be delayed by 15-20 minutes")
    print("For real-time data, consider using IB or Polygon providers")
    
    # Run tests
    try:
        # Test individual symbols with cleanup between tests
        asyncio.run(test_live_data_for_symbol("SPY"))
        asyncio.run(cleanup_connections())
        
        asyncio.run(test_live_data_for_symbol("QQQ"))
        asyncio.run(cleanup_connections())
        
        # Test full recommendation engine
        asyncio.run(test_live_recommendations())
        asyncio.run(cleanup_connections())
        
        # Compare mock vs live
        asyncio.run(compare_mock_vs_live())
        asyncio.run(cleanup_connections())
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        # Ensure cleanup on interrupt
        asyncio.run(cleanup_connections())
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        # Ensure cleanup on error
        asyncio.run(cleanup_connections())
        sys.exit(1)


if __name__ == "__main__":
    main()