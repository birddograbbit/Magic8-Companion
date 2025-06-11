#!/usr/bin/env python
"""
Test Enhanced Indicators with Real Market Data
Tests the enhanced scoring system with live market data from yfinance.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone
import warnings

# Suppress yfinance warnings
warnings.filterwarnings('ignore', module='yfinance')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magic8_companion.modules.enhanced_combo_scorer import EnhancedComboScorer
from magic8_companion.modules.market_analysis_simplified import MarketAnalyzer


async def test_real_market_data(symbols: list = None):
    """Test enhanced scoring with real market data."""
    if symbols is None:
        symbols = ['SPY', 'QQQ', 'IWM']  # Default test symbols
    
    print("="*60)
    print("Magic8-Companion Real Market Data Test")
    print("="*60)
    print(f"Testing with symbols: {', '.join(symbols)}")
    print("Data source: Yahoo Finance (yfinance)")
    print("="*60)
    
    # Enable all enhancements and real data
    os.environ['M8C_ENABLE_GREEKS'] = 'true'
    os.environ['M8C_ENABLE_ADVANCED_GEX'] = 'true'
    os.environ['M8C_ENABLE_VOLUME_ANALYSIS'] = 'true'
    os.environ['M8C_USE_MOCK_DATA'] = 'false'  # Use real data
    
    # Initialize components
    scorer = EnhancedComboScorer()
    analyzer = MarketAnalyzer()
    
    print("\nConfiguration:")
    print(f"  Mock Data: DISABLED (using real market data)")
    status = scorer.get_enhancement_status()
    for feature, enabled in status.items():
        print(f"  {feature}: {'✓ Enabled' if enabled else '✗ Disabled'}")
    
    # Test each symbol
    results_summary = {}
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Analyzing {symbol}...")
        print("="*60)
        
        try:
            # Get real market data
            market_data = await analyzer.analyze_symbol(symbol)
            
            if not market_data:
                print(f"❌ Failed to fetch data for {symbol}")
                continue
            
            # Display fetched data
            print(f"\nMarket Data Retrieved:")
            print(f"  Data Source: {'Real (Yahoo Finance)' if not market_data.get('is_mock_data') else 'Mock (Fallback)'}")
            print(f"  Spot Price: ${market_data.get('spot_price', 'N/A'):.2f}" if 'spot_price' in market_data else "  Spot Price: N/A")
            print(f"  IV Percentile: {market_data.get('iv_percentile', 'N/A')}")
            print(f"  Expected Range: {market_data.get('expected_range_pct', 0):.2%}")
            print(f"  Gamma Environment: {market_data.get('gamma_environment', 'N/A')}")
            
            if 'option_chain' in market_data and market_data['option_chain']:
                print(f"  Option Chain: {len(market_data['option_chain'])} strikes loaded")
                
                # Show sample option data
                sample_opt = market_data['option_chain'][len(market_data['option_chain'])//2]
                print(f"\n  Sample Option Data (ATM):")
                print(f"    Strike: ${sample_opt['strike']:.2f}")
                print(f"    IV: {sample_opt['implied_volatility']:.1%}")
                print(f"    Call OI: {sample_opt['call_open_interest']:,}")
                print(f"    Put OI: {sample_opt['put_open_interest']:,}")
                print(f"    Call Volume: {sample_opt['call_volume']:,}")
                print(f"    Put Volume: {sample_opt['put_volume']:,}")
            else:
                print(f"  Option Chain: No data available")
            
            # Score strategies
            if 'option_chain' in market_data and market_data['option_chain']:
                print(f"\nStrategy Scores:")
                results = scorer.score_all_strategies(market_data)
                
                # Sort by score
                sorted_strategies = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
                
                for i, (strategy, result) in enumerate(sorted_strategies):
                    status_icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                    print(f"\n  {status_icon} {strategy}:")
                    print(f"     Score: {result['score']:.1f} ({result['confidence']})")
                    print(f"     Trade: {'✓ YES' if result['should_trade'] else '✗ NO'}")
                
                # Store results
                best_strategy = sorted_strategies[0][0]
                best_score = sorted_strategies[0][1]['score']
                
                results_summary[symbol] = {
                    'best_strategy': best_strategy,
                    'best_score': best_score,
                    'all_scores': {k: v['score'] for k, v in results.items()},
                    'market_conditions': {
                        'spot_price': market_data.get('spot_price'),
                        'iv_percentile': market_data.get('iv_percentile'),
                        'expected_range_pct': market_data.get('expected_range_pct'),
                        'gamma_environment': market_data.get('gamma_environment')
                    }
                }
                
                print(f"\n  📊 Recommendation: {best_strategy} (Score: {best_score:.1f})")
            else:
                print("\n  ⚠️  Cannot score strategies - no option chain data")
                results_summary[symbol] = {'error': 'No option chain data available'}
                
        except Exception as e:
            print(f"\n❌ Error analyzing {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            results_summary[symbol] = {'error': str(e)}
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY - Best Strategies by Symbol:")
    print("="*60)
    
    for symbol, data in results_summary.items():
        if 'error' in data:
            print(f"{symbol}: Error - {data['error']}")
        else:
            print(f"{symbol}: {data['best_strategy']} (Score: {data['best_score']:.1f})")
    
    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"real_market_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'symbols_tested': symbols,
            'results': results_summary,
            'configuration': {
                'enhancements': scorer.get_enhancement_status(),
                'data_source': 'yfinance'
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {filename}")
    
    return results_summary


async def test_market_hours_check():
    """Check if market is open and provide guidance."""
    from datetime import datetime
    import pytz
    
    # Get current time in ET
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    
    print("\nMarket Hours Check:")
    print(f"Current time (ET): {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Check if it's a weekday
    if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
        print("⚠️  Market is CLOSED (Weekend)")
        print("   Option data may be stale or unavailable")
    else:
        # Check market hours (9:30 AM - 4:00 PM ET)
        market_open = now_et.replace(hour=9, minute=30, second=0)
        market_close = now_et.replace(hour=16, minute=0, second=0)
        
        if market_open <= now_et <= market_close:
            print("✅ Market is OPEN")
            print("   Real-time data should be available")
        else:
            print("⚠️  Market is CLOSED (After hours)")
            print("   Option data may be from last trading session")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test enhanced indicators with real market data')
    parser.add_argument('symbols', nargs='*', default=['SPY', 'QQQ', 'IWM'],
                       help='Symbols to test (default: SPY QQQ IWM)')
    parser.add_argument('--check-hours', action='store_true',
                       help='Check market hours before testing')
    
    args = parser.parse_args()
    
    if args.check_hours:
        await test_market_hours_check()
    
    # Run the test
    await test_real_market_data(args.symbols)
    
    print("\n" + "="*60)
    print("Real market data test complete!")
    print("\nNext steps:")
    print("1. Review scores across different market conditions")
    print("2. Compare with your manual analysis")
    print("3. Fine-tune thresholds based on real market behavior")
    print("4. Consider testing during different market sessions")
    print("5. Monitor performance over multiple days")


if __name__ == "__main__":
    asyncio.run(main())
