"""
Quick fix script to test SPX with direct SPXW symbol.
Run this to see if using SPXW directly works.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from magic8_companion.modules.ibkr_market_data import IBKRMarketData, IBKRConnection


async def test_spx_as_spxw():
    """Test if we can get SPX data by using SPXW directly."""
    ibkr = IBKRMarketData()
    
    # Temporarily override the symbol map
    ibkr.symbol_map['SPX'] = 'SPXW'  # Map SPX to SPXW
    
    async with IBKRConnection(ibkr) as market_data:
        print("Testing SPX (mapped to SPXW)...")
        data = await market_data.get_market_data("SPX")
        
        if data:
            print(f"✅ Success! Got data for SPX via SPXW")
            print(f"Spot Price: ${data['spot_price']:.2f}")
            print(f"Option Strikes: {len(data['option_chain'])}")
            if data['option_chain']:
                print(f"First strike: ${data['option_chain'][0]['strike']}")
                print(f"Last strike: ${data['option_chain'][-1]['strike']}")
        else:
            print("❌ Still failed with SPXW mapping")


if __name__ == "__main__":
    asyncio.run(test_spx_as_spxw())
