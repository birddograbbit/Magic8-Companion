#!/usr/bin/env python3
"""
Test script to verify the NaN open interest fix.
This tests that the IBKR module can now handle NaN values in open interest fields.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magic8_companion.modules.ibkr_market_data import IBKRMarketData, IBKRConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_nan_fix():
    """Test that the NaN open interest fix works correctly."""
    print("=" * 60)
    print("Testing NaN Open Interest Fix")
    print("=" * 60)
    print()
    
    # Test symbols
    test_symbols = ['SPX', 'SPY']
    results = {}
    
    ibkr = IBKRMarketData()
    
    try:
        async with IBKRConnection(ibkr) as market_data:
            for symbol in test_symbols:
                print(f"Testing {symbol}...")
                try:
                    data = await market_data.get_market_data(symbol)
                    
                    if data and data.get('option_chain'):
                        # Check for open interest values
                        chain = data['option_chain']
                        total_strikes = len(chain)
                        
                        # Count strikes with valid open interest
                        strikes_with_oi = 0
                        strikes_with_zero_oi = 0
                        
                        for option in chain:
                            call_oi = option.get('call_open_interest', 0)
                            put_oi = option.get('put_open_interest', 0)
                            
                            # Verify these are integers
                            if not isinstance(call_oi, int) or not isinstance(put_oi, int):
                                print(f"❌ Non-integer OI found: call={call_oi}, put={put_oi}")
                                results[symbol] = "FAILED - Non-integer OI"
                                break
                            
                            if call_oi > 0 or put_oi > 0:
                                strikes_with_oi += 1
                            else:
                                strikes_with_zero_oi += 1
                        
                        else:  # No break occurred
                            print(f"✅ SUCCESS - Retrieved {total_strikes} strikes")
                            print(f"   - Strikes with OI > 0: {strikes_with_oi}")
                            print(f"   - Strikes with OI = 0: {strikes_with_zero_oi}")
                            print(f"   - Spot Price: ${data['spot_price']:.2f}")
                            print(f"   - Data Source: {data['data_source']}")
                            
                            # Show sample strike data
                            if chain:
                                mid_strike = chain[len(chain)//2]
                                print(f"   - Sample Strike {mid_strike['strike']}:")
                                print(f"     - Call OI: {mid_strike['call_open_interest']}")
                                print(f"     - Put OI: {mid_strike['put_open_interest']}")
                            
                            results[symbol] = "SUCCESS"
                    else:
                        print(f"❌ FAILED - No option chain data")
                        results[symbol] = "FAILED - No data"
                        
                except Exception as e:
                    print(f"❌ FAILED - Exception: {str(e)}")
                    results[symbol] = f"FAILED - {str(e)}"
                
                print()
                
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return False
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = all(result == "SUCCESS" for result in results.values())
    
    for symbol, result in results.items():
        status = "✅" if result == "SUCCESS" else "❌"
        print(f"{status} {symbol}: {result}")
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED! The NaN fix is working correctly.")
        print("   Open interest values are now properly handled as integers.")
    else:
        print("⚠️  SOME TESTS FAILED. Please check the errors above.")
        print("   Note: If market is closed, you may see all zero OI values.")
    
    return all_passed


async def main():
    """Main test function."""
    success = await test_nan_fix()
    
    print("\n" + "=" * 60)
    print("Additional Notes:")
    print("- NaN values are now converted to 0 instead of causing errors")
    print("- This fix handles market closed scenarios gracefully")
    print("- Open interest may be 0 for all strikes if market is closed")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
