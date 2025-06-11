#!/usr/bin/env python3
"""
Test script to verify the OI streaming fix for IBKR.
This tests that the IBKR module can now properly retrieve Open Interest data.
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


async def test_oi_streaming():
    """Test that the OI streaming implementation works correctly."""
    print("=" * 60)
    print("Testing IBKR Open Interest Streaming Fix")
    print("=" * 60)
    print()
    
    # Test symbols
    test_symbols = ['SPX', 'SPY']
    results = {}
    
    ibkr = IBKRMarketData()
    
    try:
        async with IBKRConnection(ibkr) as market_data:
            for symbol in test_symbols:
                print(f"\nTesting {symbol}...")
                print("-" * 40)
                
                try:
                    start_time = datetime.now()
                    data = await market_data.get_market_data(symbol)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if data and data.get('option_chain'):
                        chain = data['option_chain']
                        total_strikes = len(chain)
                        
                        # Analyze OI data
                        strikes_with_call_oi = 0
                        strikes_with_put_oi = 0
                        total_call_oi = 0
                        total_put_oi = 0
                        max_call_oi = 0
                        max_put_oi = 0
                        
                        for option in chain:
                            call_oi = option.get('call_open_interest', 0)
                            put_oi = option.get('put_open_interest', 0)
                            
                            if call_oi > 0:
                                strikes_with_call_oi += 1
                                total_call_oi += call_oi
                                max_call_oi = max(max_call_oi, call_oi)
                            
                            if put_oi > 0:
                                strikes_with_put_oi += 1
                                total_put_oi += put_oi
                                max_put_oi = max(max_put_oi, put_oi)
                        
                        oi_success_rate = ((strikes_with_call_oi + strikes_with_put_oi) / (total_strikes * 2)) * 100
                        
                        print(f"✅ SUCCESS - Retrieved {total_strikes} strikes in {elapsed:.1f}s")
                        print(f"   Spot Price: ${data['spot_price']:.2f}")
                        print(f"   Data Source: {data['data_source']}")
                        print(f"\nOpen Interest Statistics:")
                        print(f"   Strikes with Call OI > 0: {strikes_with_call_oi}/{total_strikes} ({strikes_with_call_oi/total_strikes*100:.1f}%)")
                        print(f"   Strikes with Put OI > 0: {strikes_with_put_oi}/{total_strikes} ({strikes_with_put_oi/total_strikes*100:.1f}%)")
                        print(f"   Total Call OI: {total_call_oi:,}")
                        print(f"   Total Put OI: {total_put_oi:,}")
                        print(f"   Max Call OI: {max_call_oi:,}")
                        print(f"   Max Put OI: {max_put_oi:,}")
                        print(f"   OI Success Rate: {oi_success_rate:.1f}%")
                        
                        # Show sample strikes
                        print(f"\nSample Strike Data:")
                        # ATM strike
                        atm_strike = min(chain, key=lambda x: abs(x['strike'] - data['spot_price']))
                        print(f"   ATM Strike {atm_strike['strike']}:")
                        print(f"     Call: Bid=${atm_strike['call_bid']:.2f}, Ask=${atm_strike['call_ask']:.2f}, OI={atm_strike['call_open_interest']:,}")
                        print(f"     Put:  Bid=${atm_strike['put_bid']:.2f}, Ask=${atm_strike['put_ask']:.2f}, OI={atm_strike['put_open_interest']:,}")
                        
                        # Strike with highest OI
                        max_oi_strike = max(chain, key=lambda x: x['call_open_interest'] + x['put_open_interest'])
                        if max_oi_strike != atm_strike:
                            print(f"   Max OI Strike {max_oi_strike['strike']}:")
                            print(f"     Call OI: {max_oi_strike['call_open_interest']:,}")
                            print(f"     Put OI: {max_oi_strike['put_open_interest']:,}")
                        
                        results[symbol] = "SUCCESS" if oi_success_rate > 0 else "PARTIAL"
                    else:
                        print(f"❌ FAILED - No option chain data")
                        results[symbol] = "FAILED - No data"
                        
                except Exception as e:
                    print(f"❌ FAILED - Exception: {str(e)}")
                    results[symbol] = f"FAILED - {str(e)}"
                
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_success = all("SUCCESS" in result for result in results.values())
    
    for symbol, result in results.items():
        if "SUCCESS" in result:
            status = "✅"
        elif "PARTIAL" in result:
            status = "⚠️"
        else:
            status = "❌"
        print(f"{status} {symbol}: {result}")
    
    print()
    if all_success:
        print("🎉 ALL TESTS PASSED! Open Interest data is being retrieved successfully.")
        print("   The streaming approach is working correctly.")
    else:
        print("⚠️  Some issues detected. Check the results above.")
        print("   Note: During market hours, you should see non-zero OI values.")
        print("   Outside market hours, OI might still be available but could be limited.")
    
    return all_success


async def main():
    """Main test function."""
    print("IBKR Open Interest Streaming Test")
    print("This test verifies that the two-phase approach works:")
    print("1. Snapshot for prices and Greeks")
    print("2. Brief streaming for Open Interest data")
    print()
    
    success = await test_oi_streaming()
    
    print("\n" + "=" * 60)
    print("Implementation Notes:")
    print("- OI data requires streaming (generic ticks 100, 101)")
    print("- Snapshot mode cannot retrieve OI data from IBKR")
    print("- The fix uses a 2-second streaming window for OI")
    print("- Both NaN handling and streaming are implemented")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
