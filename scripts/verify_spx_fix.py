#!/usr/bin/env python3
"""
Verify SPX option chain fix - test if we can now get SPX options correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from magic8_companion.modules.ibkr_market_data import IBKRMarketData, IBKRConnection


async def verify_spx_fix():
    """Verify that SPX option chains now work correctly."""
    print("="*60)
    print("Verifying SPX Option Chain Fix")
    print("="*60)
    
    ibkr = IBKRMarketData()
    
    async with IBKRConnection(ibkr) as market_data:
        # Test SPX
        print("\nTesting SPX...")
        data = await market_data.get_market_data("SPX")
        
        if data:
            print(f"✅ SUCCESS! SPX option chain retrieved")
            print(f"\nMarket Data:")
            print(f"  Symbol: {data['symbol']}")
            print(f"  Spot Price: ${data['spot_price']:.2f}")
            print(f"  IV Percentile: {data['iv_percentile']:.1f}%")
            print(f"  Expected Range: ±{data['expected_range_pct']:.2%}")
            print(f"  Gamma Environment: {data['gamma_environment']}")
            print(f"  Data Source: {data['data_source']}")
            
            if data['option_chain']:
                print(f"\nOption Chain:")
                print(f"  Total Strikes: {len(data['option_chain'])}")
                print(f"  Strike Range: ${data['option_chain'][0]['strike']:.0f} - ${data['option_chain'][-1]['strike']:.0f}")
                
                # Show ATM option
                spot = data['spot_price']
                atm = min(data['option_chain'], key=lambda x: abs(x['strike'] - spot))
                print(f"\n  ATM Option (Strike ${atm['strike']:.0f}):")
                print(f"    IV: {atm['implied_volatility']*100:.1f}%")
                print(f"    Call Delta: {atm['call_delta']:.3f}")
                print(f"    Call Gamma: {atm['call_gamma']:.6f}")
                print(f"    Volume: Call={atm['call_volume']}, Put={atm['put_volume']}")
        else:
            print("❌ FAILED - Still unable to get SPX data")
            print("Please check:")
            print("1. TWS is running and connected")
            print("2. You have SPX market data subscription")
            print("3. Market is open (or use snapshot data)")
        
        # Also test SPY for comparison
        print("\n" + "-"*40)
        print("Testing SPY for comparison...")
        spy_data = await market_data.get_market_data("SPY")
        
        if spy_data:
            print(f"✅ SPY works: Price=${spy_data['spot_price']:.2f}, Strikes={len(spy_data['option_chain'])}")
        else:
            print("❌ SPY also failed - check IBKR connection")


if __name__ == "__main__":
    asyncio.run(verify_spx_fix())
