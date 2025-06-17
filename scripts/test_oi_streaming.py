"""
Quick test script to verify OI streaming with ib_async
"""
import asyncio
from ib_async import IB, Option
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_oi_streaming():
    """Test if we can get OI data via streaming"""
    ib = IB()
    
    try:
        # Connect to IB
        await ib.connectAsync("127.0.0.1", 7497, clientId=999)
        print("Connected to IB")
        
        # Create a simple SPX option contract
        option = Option(
            symbol="SPXW",
            lastTradeDateOrContractMonth="20250617",  # Today's date
            strike=6000,
            right="C",
            exchange="SMART",
            currency="USD"
        )
        option.tradingClass = "SPXW"
        
        # Qualify the contract
        qualified = await ib.qualifyContractsAsync(option)
        if not qualified or not qualified[0].conId:
            print("Failed to qualify contract")
            return
            
        contract = qualified[0]
        print(f"Qualified contract: {contract.symbol} {contract.strike} {contract.right}")
        
        # Method 1: Try snapshot with OI generic ticks
        print("\nMethod 1: Snapshot with OI ticks...")
        ticker = ib.reqMktData(contract, genericTickList="100,101,106,107", snapshot=True)
        await asyncio.sleep(2)
        
        print(f"Ticker attributes: {list(ticker.__dict__.keys())}")
        print(f"Open Interest: {getattr(ticker, 'openInterest', 'Not found')}")
        print(f"Call OI: {getattr(ticker, 'callOpenInterest', 'Not found')}")
        
        # Method 2: Try streaming with OI generic ticks
        print("\nMethod 2: Streaming with OI ticks...")
        ib.cancelMktData(contract)
        ticker2 = ib.reqMktData(contract, genericTickList="100,101", snapshot=False)
        
        # Wait for data
        for i in range(5):
            await asyncio.sleep(1)
            print(f"  Attempt {i+1}: OI={getattr(ticker2, 'openInterest', 'Not found')}, "
                  f"Call OI={getattr(ticker2, 'callOpenInterest', 'Not found')}")
            
            # Check if we have any tick data
            if hasattr(ticker2, 'ticks') and ticker2.ticks:
                print(f"  Ticks received: {ticker2.ticks}")
        
        # Cancel streaming
        ib.cancelMktData(contract)
        
        # Method 3: Check available tick types
        print("\nAvailable data from snapshot:")
        ticker3 = ib.reqMktData(contract, genericTickList="", snapshot=True)
        await asyncio.sleep(2)
        
        for attr in dir(ticker3):
            if not attr.startswith('_'):
                value = getattr(ticker3, attr, None)
                if value is not None and not callable(value):
                    print(f"  {attr}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ib.disconnect()
        print("\nDisconnected")

if __name__ == "__main__":
    asyncio.run(test_oi_streaming())
