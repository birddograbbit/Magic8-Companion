"""
Test script to diagnose OI and volume data issues
"""
import asyncio
import logging
from magic8_companion.modules.ib_client import IBClient
from magic8_companion.modules.ib_oi_fetcher import IBOpenInterestFetcher

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ib_data():
    """Test IB data fetching with detailed logging"""
    client = IBClient()
    
    try:
        await client._ensure_connected()
        print("\n=== Testing IB Data Fetching ===\n")
        
        # Test basic option data
        print("1. Testing basic option data fetch...")
        options = await client.get_atm_options(['SPX'], days_to_expiry=0)
        
        if options:
            print(f"   Found {len(options)} options")
            # Check first few options
            for i, opt in enumerate(options[:3]):
                print(f"\n   Option {i+1}:")
                print(f"   Strike: {opt['strike']} {opt['right']}")
                print(f"   Bid/Ask: {opt['bid']}/{opt['ask']}")
                print(f"   IV: {opt['implied_volatility']}")
                print(f"   Gamma: {opt['gamma']}")
                print(f"   OI: {opt['open_interest']}")
                
                # Check what other fields might be available
                print(f"   All fields: {list(opt.keys())}")
        else:
            print("   ERROR: No options data returned")
        
        # Test OI fetcher specifically
        print("\n2. Testing OI fetcher...")
        if client.oi_fetcher and options:
            # Get the first 5 contracts for testing
            test_contracts = []
            for opt in options[:5]:
                from ib_async import Option
                contract = Option(
                    symbol='SPXW',  # Use SPXW for SPX options
                    lastTradeDateOrContractMonth=opt['expiry'],
                    strike=opt['strike'],
                    right=opt['right'],
                    exchange='SMART',
                    currency='USD'
                )
                contract.conId = opt['conId']  # Use the conId from qualified contract
                test_contracts.append(contract)
            
            oi_data = await client.oi_fetcher.get_oi_data_streaming(test_contracts, timeout=5.0)
            print(f"   OI data retrieved: {oi_data}")
        
        # Check market data for volume
        print("\n3. Checking ticker data for volume...")
        from ib_async import Index
        spx_index = Index('SPX', 'CBOE', 'USD')
        qualified = await client.ib.qualifyContractsAsync(spx_index)
        if qualified:
            ticker = await client.ib.reqTickersAsync(qualified[0])
            if ticker:
                print(f"   SPX ticker attributes: {[attr for attr in dir(ticker[0]) if not attr.startswith('_')]}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

async def main():
    """Run the test"""
    await test_ib_data()

if __name__ == '__main__':
    asyncio.run(main())
