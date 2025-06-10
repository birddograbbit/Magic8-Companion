#!/usr/bin/env python
"""
Test Enhanced Indicators
Demonstrates the enhanced scoring system with all new indicators.
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magic8_companion.modules.enhanced_combo_scorer import EnhancedComboScorer
from magic8_companion.modules.market_analysis_simplified import MarketAnalyzer


async def test_enhanced_scoring():
    """Test enhanced scoring with mock data."""
    print("="*60)
    print("Magic8-Companion Enhanced Indicators Test")
    print("="*60)
    
    # Enable all enhancements
    os.environ['ENABLE_GREEKS'] = 'true'
    os.environ['ENABLE_ADVANCED_GEX'] = 'true'
    os.environ['ENABLE_VOLUME_ANALYSIS'] = 'true'
    os.environ['USE_MOCK_DATA'] = 'true'
    
    # Initialize components
    scorer = EnhancedComboScorer()
    analyzer = MarketAnalyzer()
    
    print("\nEnhancement Status:")
    status = scorer.get_enhancement_status()
    for feature, enabled in status.items():
        print(f"  {feature}: {'✓ Enabled' if enabled else '✗ Disabled'}")
    
    # Get mock market data
    print("\n" + "="*60)
    print("Fetching market data...")
    market_data_raw = await analyzer.analyze_symbol('SPX')
    
    # Convert to the format expected by scorer
    market_data = {
        'iv_rank': market_data_raw['iv_percentile'],
        'range_expectation': market_data_raw['expected_range_pct'],
        'gamma_environment': market_data_raw['gamma_environment'],
        'spot_price': 5850,  # Mock spot price
        'time_to_expiry': 1/365  # 0DTE
    }
    
    # Add mock option chain data for enhanced indicators
    market_data['option_chain'] = generate_mock_option_chain(market_data['spot_price'])
    
    print(f"\nMarket Conditions:")
    print(f"  Spot Price: ${market_data['spot_price']:,.2f}")
    print(f"  IV Rank: {market_data['iv_rank']}")
    print(f"  Expected Range: {market_data['range_expectation']:.2%}")
    print(f"  Option Chain: {len(market_data['option_chain'])} strikes")
    
    # Score all strategies
    print("\n" + "="*60)
    print("Strategy Scoring Results:")
    print("="*60)
    
    results = scorer.score_all_strategies(market_data)
    
    # Sort by score
    sorted_strategies = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for strategy, result in sorted_strategies:
        print(f"\n{strategy}:")
        print(f"  Total Score: {result['score']:.1f} ({result['confidence']})")
        print(f"  Should Trade: {'✓ YES' if result['should_trade'] else '✗ NO'}")
        
        if 'components' in result:
            components = result['components']
            print(f"\n  Score Breakdown:")
            print(f"    Base Score: {components['base_score']:.1f}")
            
            if 'greeks_adjustments' in components:
                print(f"\n    Greeks Adjustments:")
                for k, v in components['greeks_adjustments'].items():
                    if v != 0:
                        print(f"      {k}: {v:+.1f}")
            
            if 'gex_adjustments' in components:
                print(f"\n    GEX Adjustments:")
                for k, v in components['gex_adjustments'].items():
                    if v != 0:
                        print(f"      {k}: {v:+.1f}")
            
            if 'volume_adjustments' in components:
                print(f"\n    Volume/OI Adjustments:")
                for k, v in components['volume_adjustments'].items():
                    if v != 0:
                        print(f"      {k}: {v:+.1f}")
    
    # Best strategy
    best_strategy = sorted_strategies[0][0]
    best_score = sorted_strategies[0][1]['score']
    
    print("\n" + "="*60)
    print(f"Recommended Strategy: {best_strategy} (Score: {best_score:.1f})")
    print("="*60)
    
    # Test with enhancements disabled
    print("\n\nTesting with enhancements disabled...")
    os.environ['ENABLE_GREEKS'] = 'false'
    os.environ['ENABLE_ADVANCED_GEX'] = 'false'
    os.environ['ENABLE_VOLUME_ANALYSIS'] = 'false'
    
    scorer_basic = EnhancedComboScorer()
    results_basic = scorer_basic.score_all_strategies(market_data)
    
    print("\nComparison (Enhanced vs Basic):")
    print(f"{'Strategy':<15} {'Enhanced':>10} {'Basic':>10} {'Difference':>12}")
    print("-" * 50)
    for strategy in results.keys():
        enhanced = results[strategy]['score']
        basic = results_basic[strategy]['score']
        diff = enhanced - basic
        print(f"{strategy:<15} {enhanced:>10.1f} {basic:>10.1f} {diff:>+12.1f}")


def generate_mock_option_chain(spot_price):
    """Generate realistic mock option chain data."""
    import numpy as np
    
    # Generate strikes around spot
    strikes = []
    for i in range(-10, 11):
        strike = round(spot_price + i * 5, 0)
        strikes.append(strike)
    
    option_chain = []
    
    for strike in strikes:
        # Distance from spot affects IV
        distance = abs(strike - spot_price) / spot_price
        base_iv = 0.15 + distance * 0.05  # IV smile
        
        # ATM has highest gamma
        moneyness = strike / spot_price
        gamma_multiplier = np.exp(-((moneyness - 1) ** 2) / 0.002)
        
        # Generate realistic values
        call_oi = np.random.randint(1000, 10000)
        put_oi = np.random.randint(1000, 10000)
        
        # Volume typically 20-50% of OI
        call_volume = int(call_oi * np.random.uniform(0.2, 0.5))
        put_volume = int(put_oi * np.random.uniform(0.2, 0.5))
        
        # Add some unusual activity
        if np.random.random() < 0.1:  # 10% chance
            if np.random.random() < 0.5:
                call_volume *= 5  # Unusual call activity
            else:
                put_volume *= 5  # Unusual put activity
        
        option_chain.append({
            'strike': strike,
            'implied_volatility': base_iv,
            'call_gamma': 0.002 * gamma_multiplier,
            'put_gamma': 0.002 * gamma_multiplier * 0.8,  # Puts typically lower
            'call_open_interest': call_oi,
            'put_open_interest': put_oi,
            'call_volume': call_volume,
            'put_volume': put_volume
        })
    
    return option_chain


async def save_test_results():
    """Save test results to file for documentation."""
    os.environ['ENABLE_GREEKS'] = 'true'
    os.environ['ENABLE_ADVANCED_GEX'] = 'true'
    os.environ['ENABLE_VOLUME_ANALYSIS'] = 'true'
    os.environ['USE_MOCK_DATA'] = 'true'
    
    scorer = EnhancedComboScorer()
    analyzer = MarketAnalyzer()
    
    # Get market data
    market_data_raw = await analyzer.analyze_symbol('SPX')
    market_data = {
        'iv_rank': market_data_raw['iv_percentile'],
        'range_expectation': market_data_raw['expected_range_pct'],
        'gamma_environment': market_data_raw['gamma_environment'],
        'spot_price': 5850,
        'time_to_expiry': 1/365,
        'option_chain': generate_mock_option_chain(5850)
    }
    
    results = scorer.score_all_strategies(market_data)
    
    # Create enhanced recommendation format
    recommendation = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checkpoint_time": datetime.now().strftime("%H:%M ET"),
        "enhanced_indicators": True,
        "recommendations": {
            "SPX": {
                "strategies": results,
                "best_strategy": max(results.items(), key=lambda x: x[1]['score'])[0],
                "market_conditions": {
                    "iv_rank": market_data['iv_rank'],
                    "range_expectation": market_data['range_expectation'],
                    "gamma_environment": market_data['gamma_environment'],
                    "spot_price": market_data['spot_price'],
                    "enhancements_enabled": scorer.get_enhancement_status()
                }
            }
        }
    }
    
    # Save to file
    output_path = "test_enhanced_recommendations.json"
    with open(output_path, 'w') as f:
        json.dump(recommendation, f, indent=2)
    
    print(f"\nTest results saved to: {output_path}")


async def main():
    """Main entry point for async execution."""
    # Run main test
    await test_enhanced_scoring()
    
    # Save results
    print("\n" + "="*60)
    await save_test_results()
    
    print("\nEnhanced indicators test complete!")
    print("\nNext steps:")
    print("1. Review the score differences between enhanced and basic")
    print("2. Fine-tune adjustment weights based on backtesting")
    print("3. Test with real market data when ready")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
