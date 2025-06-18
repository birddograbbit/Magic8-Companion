"""
Test script to diagnose OI and volume data issues
"""
import asyncio
import logging
from magic8_companion.modules.ib_client import IBClient
from magic8_companion.modules.ib_oi_fetcher import IBOpenInterestFetcher
from datetime import datetime

# Setup logging - reduce noise
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

async def test_ib_data():
    """Test IB data fetching with clear results summary"""
    client = IBClient()
    
    print("\n" + "="*60)
    print(f"IB Open Interest Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        await client._ensure_connected()
        print("\n✓ Connected to IB successfully")
        
        # Test basic option data
        print("\n1. Fetching SPX options...")
        options = await client.get_atm_options(['SPX'], days_to_expiry=0)
        
        if not options:
            print("   ERROR: No options data returned")
            return
            
        print(f"   ✓ Found {len(options)} total options")
        
        # Analyze the OI data in the returned options
        options_with_oi = 0
        total_oi = 0
        calls_with_oi = 0
        puts_with_oi = 0
        
        for opt in options:
            if opt.get('open_interest', 0) > 0:
                options_with_oi += 1
                total_oi += opt['open_interest']
                if opt['right'] == 'C':
                    calls_with_oi += 1
                else:
                    puts_with_oi += 1
        
        print(f"\n2. Open Interest Summary:")
        print(f"   • Options with OI data: {options_with_oi}/{len(options)} ({options_with_oi/len(options)*100:.1f}%)")
        print(f"   • Calls with OI: {calls_with_oi}")
        print(f"   • Puts with OI: {puts_with_oi}")
        print(f"   • Total OI across all strikes: {total_oi:,}")
        
        # Show sample of data
        print(f"\n3. Sample Data (first 5 strikes around ATM):")
        print(f"   {'Strike':<8} {'Type':<5} {'Bid':<8} {'Ask':<8} {'IV':<8} {'OI':<10}")
        print("   " + "-"*50)
        
        # Find ATM and show nearby strikes
        spot_price = options[0].get('underlying_price_at_fetch', 0)
        atm_options = sorted(options, key=lambda x: abs(x['strike'] - spot_price))[:10]
        
        for opt in sorted(atm_options[:5], key=lambda x: (x['strike'], x['right'])):
            print(f"   {opt['strike']:<8.0f} {opt['right']:<5} "
                  f"{opt.get('bid', 0):<8.2f} {opt.get('ask', 0):<8.2f} "
                  f"{opt.get('implied_volatility', 0)*100:<8.1f} {opt.get('open_interest', 0):<10,}")
        
        # Test OI fetcher directly with a smaller batch
        print(f"\n4. Testing Direct OI Fetcher (5 contracts)...")
        if client.oi_fetcher and options:
            from ib_async import Option
            
            # Get 5 near-ATM contracts
            test_options = atm_options[:5]
            test_contracts = []
            
            for opt in test_options:
                contract = Option(
                    symbol='SPXW',
                    lastTradeDateOrContractMonth=opt['expiry'],
                    strike=opt['strike'],
                    right=opt['right'],
                    exchange='SMART',
                    currency='USD'
                )
                contract.conId = opt['conId']
                test_contracts.append(contract)
            
            # Test with different timeouts
            for timeout in [3.0, 5.0, 10.0]:
                print(f"\n   Testing with {timeout}s timeout...")
                oi_data = await client.oi_fetcher.get_oi_data_streaming(test_contracts, timeout=timeout)
                print(f"   → Retrieved OI for {len(oi_data)}/{len(test_contracts)} contracts ({len(oi_data)/len(test_contracts)*100:.0f}%)")
                
                if len(oi_data) == len(test_contracts):
                    print(f"   ✓ SUCCESS: All contracts got OI data with {timeout}s timeout")
                    break
        
        # Final summary
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"{'='*60}")
        print(f"Total options tested: {len(options)}")
        print(f"Options with OI data: {options_with_oi} ({options_with_oi/len(options)*100:.1f}%)")
        print(f"Current spot price: ${spot_price:.2f}")
        
        if options_with_oi < len(options) * 0.5:
            print("\n⚠️  WARNING: Less than 50% of options have OI data!")
            print("   Possible causes:")
            print("   - Market may be closed (OI updates during market hours)")
            print("   - Timeout may be too short")
            print("   - Rate limiting from IB")
        else:
            print("\n✓ OI data retrieval is working properly")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n✓ Disconnected from IB")

async def main():
    """Run the test"""
    await test_ib_data()

if __name__ == '__main__':
    print("Starting IB Open Interest test...")
    print("Make sure TWS/Gateway is running and API is enabled.")
    asyncio.run(main())
