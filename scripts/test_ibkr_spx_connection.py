#!/usr/bin/env python
"""
Test IBKR SPX/SPXW connectivity after fixes.
This script specifically tests the symbol and exchange fallback logic.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from magic8_companion.modules.ib_client import IBClient
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for our modules
logging.getLogger('magic8_companion.modules.ib_client').setLevel(logging.DEBUG)

async def test_ibkr_spx_connection():
    """Test IBKR connection with SPX/SPXW fallback."""
    print("=" * 60)
    print("IBKR SPX/SPXW Connection Test")
    print("=" * 60)
    
    client = IBClient()
    
    try:
        # Test connection
        print("\n1. Testing IBKR connection...")
        await client._ensure_connected()
        print("✅ Successfully connected to IBKR")
        
        # Test underlying qualification for SPX
        print("\n2. Testing SPX underlying qualification...")
        underlying = await client.qualify_underlying_with_fallback('SPX')
        if underlying:
            print(f"✅ Qualified SPX underlying:")
            print(f"   Symbol: {underlying.symbol}")
            print(f"   Exchange: {underlying.exchange}")
            print(f"   ConId: {underlying.conId}")
            print(f"   SecType: {underlying.secType}")
        else:
            print("❌ Failed to qualify SPX underlying")
            
        # Test option qualification
        print("\n3. Testing SPX option qualification...")
        from datetime import datetime
        expiry = datetime.now().strftime('%Y%m%d')
        
        # Try to qualify a specific SPX option
        test_strike = 6000  # Adjust based on current SPX level
        option = await client.qualify_option_with_fallback('SPX', expiry, test_strike, 'C')
        
        if option:
            print(f"✅ Qualified SPX option:")
            print(f"   Symbol: {option.symbol}")
            print(f"   Strike: {option.strike}")
            print(f"   Right: {option.right}")
            print(f"   Exchange: {option.exchange}")
            print(f"   Trading Class: {getattr(option, 'tradingClass', 'N/A')}")
            print(f"   ConId: {option.conId}")
        else:
            print(f"❌ Failed to qualify SPX {test_strike} C option")
            
        # Test get_atm_options
        print("\n4. Testing get_atm_options for SPX...")
        atm_options = await client.get_atm_options(['SPX'], days_to_expiry=0)
        
        if atm_options:
            print(f"✅ Found {len(atm_options)} ATM options for SPX:")
            # Show first few options
            for i, opt in enumerate(atm_options[:4]):
                print(f"   Option {i+1}:")
                print(f"     Strike: {opt['strike']} {opt['right']}")
                print(f"     Underlying Symbol: {opt.get('underlying_symbol', 'N/A')}")
                print(f"     Bid/Ask: {opt['bid']}/{opt['ask']}")
                print(f"     IV: {opt['implied_volatility']}")
                print(f"     OI: {opt.get('open_interest', 'N/A')}")
        else:
            print("❌ No ATM options found for SPX")
            
        # Test RUT as well
        print("\n5. Testing RUT underlying qualification...")
        rut_underlying = await client.qualify_underlying_with_fallback('RUT')
        if rut_underlying:
            print(f"✅ Qualified RUT underlying on {rut_underlying.exchange}")
        else:
            print("❌ Failed to qualify RUT underlying")
            
    except ConnectionError as e:
        print(f"❌ Connection Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n✅ Disconnected from IBKR")
        
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test_ibkr_spx_connection())
