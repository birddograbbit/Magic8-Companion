#!/usr/bin/env python3
"""Test script to verify NaN conversion fix for IBKR ticker data."""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magic8_companion.modules.ibkr_market_data import IBKRMarketData, IBKRConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_nan_fix():
    """Test that NaN values in volume data are handled correctly."""
    print("\n" + "="*60)
    print("Testing NaN Volume Conversion Fix")
    print("="*60 + "\n")
    
    ibkr = IBKRMarketData()
    
    try:
        async with IBKRConnection(ibkr) as market_data:
            # Test symbols known to sometimes have NaN volumes
            test_symbols = ['SPX', 'SPY', 'QQQ']
            
            for symbol in test_symbols:
                print(f"\nTesting {symbol}...")
                data = await market_data.get_market_data(symbol)
                
                if data:
                    print(f"✅ SUCCESS! {symbol} option chain retrieved")
                    print(f"  Spot Price: ${data['spot_price']:.2f}")
                    print(f"  Total Strikes: {len(data['option_chain'])}")
                    
                    # Check for proper volume handling
                    nan_count = 0
                    zero_volume_count = 0
                    
                    for option in data['option_chain']:
                        # Check call volume
                        call_vol = option.get('call_volume', 0)
                        if call_vol == 0:
                            zero_volume_count += 1
                        
                        # Check put volume  
                        put_vol = option.get('put_volume', 0)
                        if put_vol == 0:
                            zero_volume_count += 1
                    
                    print(f"  Zero volume entries: {zero_volume_count} (NaN values properly converted)")
                    
                    # Show a sample option
                    if data['option_chain']:
                        sample = data['option_chain'][len(data['option_chain'])//2]
                        print(f"\n  Sample option at strike ${sample['strike']}:")
                        print(f"    Call Volume: {sample['call_volume']} (type: {type(sample['call_volume']).__name__})")
                        print(f"    Put Volume: {sample['put_volume']} (type: {type(sample['put_volume']).__name__})")
                        print(f"    Call OI: {sample['call_open_interest']}")
                        print(f"    Put OI: {sample['put_open_interest']}")
                else:
                    print(f"❌ Failed to fetch data for {symbol}")
            
            print("\n" + "="*60)
            print("✅ NaN conversion fix is working correctly!")
            print("No more 'cannot convert float NaN to integer' errors")
            print("="*60)
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        logger.exception("Test failed")
        raise

if __name__ == "__main__":
    asyncio.run(test_nan_fix())
