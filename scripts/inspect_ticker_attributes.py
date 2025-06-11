#!/usr/bin/env python3
"""
Inspect Ticker object attributes to understand the correct way to access open interest.
"""

import asyncio
from ib_async import IB, Option
from datetime import datetime


async def inspect_ticker_attributes():
    """Inspect what attributes are available on Ticker objects."""
    ib = IB()
    
    try:
        await ib.connectAsync('127.0.0.1', 7497, clientId=4)
        print("Connected to IBKR")
        
        # Create a sample option contract (SPY for testing)
        option = Option(
            symbol='SPY',
            lastTradeDateOrContractMonth='20250611',
            strike=605,
            right='C',
            exchange='SMART',
            currency='USD'
        )
        
        # Qualify the contract
        contracts = await ib.qualifyContractsAsync(option)
        if contracts:
            option = contracts[0]
            print(f"Qualified option: {option.localSymbol}")
            
            # Request market data
            ticker = ib.reqMktData(option, '', True, False)  # Snapshot mode
            
            # Wait for data
            await asyncio.sleep(2)
            
            # Inspect all attributes
            print("\n=== Ticker Attributes ===")
            attrs = [attr for attr in dir(ticker) if not attr.startswith('_')]
            for attr in sorted(attrs):
                try:
                    value = getattr(ticker, attr)
                    if not callable(value):
                        print(f"{attr}: {value}")
                except Exception as e:
                    print(f"{attr}: <error: {e}>")
            
            # Specifically check for open interest related attributes
            print("\n=== Open Interest Related ===")
            oi_attrs = [attr for attr in attrs if 'open' in attr.lower() or 'interest' in attr.lower()]
            for attr in oi_attrs:
                try:
                    value = getattr(ticker, attr)
                    print(f"{attr}: {value}")
                except:
                    pass
            
            # Check if it's stored differently for options
            print("\n=== Option Specific Attributes ===")
            if hasattr(ticker, 'contract'):
                print(f"Contract type: {ticker.contract.secType}")
                print(f"Contract right: {ticker.contract.right}")
            
            # Cancel market data
            ib.cancelMktData(ticker)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ib.disconnect()
        print("\nDisconnected")


if __name__ == "__main__":
    asyncio.run(inspect_ticker_attributes())
