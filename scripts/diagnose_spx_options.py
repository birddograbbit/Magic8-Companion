#!/usr/bin/env python3
"""
Diagnostic script for SPX option chain issues with IBKR.
This script tests different approaches to get SPX option data.
"""

import asyncio
import logging
from datetime import datetime
from ib_async import IB, Index, Option, Contract

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_spx_options():
    """Test different methods to get SPX option chains."""
    ib = IB()
    
    try:
        # Connect to TWS
        await ib.connectAsync('127.0.0.1', 7497, clientId=2)
        logger.info("Connected to IBKR TWS")
        
        # Method 1: Try with Index contract
        logger.info("\n=== Method 1: Index Contract ===")
        spx_index = Index(symbol='SPX', exchange='CBOE', currency='USD')
        contracts = await ib.qualifyContractsAsync(spx_index)
        if contracts:
            spx_index = contracts[0]
            logger.info(f"Qualified SPX Index: {spx_index}")
            logger.info(f"ConId: {spx_index.conId}")
            
            # Get current price
            ticker = await ib.reqTickersAsync(spx_index)
            if ticker:
                logger.info(f"SPX Price: {ticker[0].marketPrice()}")
        
        # Method 2: Try direct option contract
        logger.info("\n=== Method 2: Direct Option Contract ===")
        # Get today's date for 0DTE
        today = datetime.now()
        exp_date = today.strftime('%Y%m%d')
        
        # Try SPXW option directly
        spxw_opt = Option(
            symbol='SPXW',
            lastTradeDateOrContractMonth=exp_date,
            strike=6100,  # Near current market
            right='C',
            exchange='SMART',
            currency='USD'
        )
        
        opt_contracts = await ib.qualifyContractsAsync(spxw_opt)
        if opt_contracts:
            logger.info(f"Found SPXW option: {opt_contracts[0]}")
            logger.info(f"Local Symbol: {opt_contracts[0].localSymbol}")
            logger.info(f"Trading Class: {opt_contracts[0].tradingClass}")
        
        # Method 3: Try reqSecDefOptParams with different parameters
        logger.info("\n=== Method 3: Option Chain Parameters ===")
        
        # Try without conId
        logger.info("Trying SPXW without conId...")
        chains1 = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol='SPXW',
            futFopExchange='',
            underlyingSecType='IND',
            underlyingConId=0  # Try without conId
        )
        logger.info(f"SPXW chains (no conId): {len(chains1) if chains1 else 0}")
        
        # Try SPX without conId
        logger.info("Trying SPX without conId...")
        chains2 = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol='SPX',
            futFopExchange='',
            underlyingSecType='IND',
            underlyingConId=0
        )
        logger.info(f"SPX chains (no conId): {len(chains2) if chains2 else 0}")
        
        # Try with SMART exchange
        logger.info("Trying SPX with SMART exchange...")
        chains3 = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol='SPX',
            futFopExchange='SMART',
            underlyingSecType='IND',
            underlyingConId=0
        )
        logger.info(f"SPX chains (SMART): {len(chains3) if chains3 else 0}")
        
        # Try with CBOE exchange
        logger.info("Trying SPX with CBOE exchange...")
        chains4 = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol='SPX',
            futFopExchange='CBOE',
            underlyingSecType='IND',
            underlyingConId=0
        )
        logger.info(f"SPX chains (CBOE): {len(chains4) if chains4 else 0}")
        
        # If we got chains, show details
        all_chains = [chains1, chains2, chains3, chains4]
        for i, chains in enumerate(all_chains):
            if chains:
                logger.info(f"\nChain set {i+1} details:")
                for j, chain in enumerate(chains):
                    logger.info(f"  Chain {j}: Exchange={chain.exchange}, "
                              f"TradingClass={chain.tradingClass}, "
                              f"Multiplier={chain.multiplier}, "
                              f"Expirations={len(chain.expirations)}, "
                              f"Strikes={len(chain.strikes)}")
                    # Show first few expirations
                    if chain.expirations:
                        logger.info(f"    First expirations: {chain.expirations[:3]}")
        
        # Method 4: Check what contracts are available
        logger.info("\n=== Method 4: Contract Details ===")
        
        # Create a generic SPX contract
        spx_generic = Contract(
            symbol='SPX',
            secType='OPT',
            exchange='SMART',
            currency='USD'
        )
        
        try:
            details = await ib.reqContractDetailsAsync(spx_generic)
            logger.info(f"Found {len(details)} SPX option contract details")
            if details:
                # Show first few
                for i, detail in enumerate(details[:3]):
                    logger.info(f"  Contract {i}: {detail.contract.localSymbol}, "
                              f"TradingClass={detail.contract.tradingClass}")
        except Exception as e:
            logger.warning(f"Contract details error: {e}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
    finally:
        ib.disconnect()
        logger.info("Disconnected from IBKR")


async def test_spy_comparison():
    """Test SPY for comparison to see what works."""
    ib = IB()
    
    try:
        await ib.connectAsync('127.0.0.1', 7497, clientId=3)
        logger.info("\n=== SPY Comparison Test ===")
        
        # Get SPY chains (this should work)
        chains = await ib.reqSecDefOptParamsAsync(
            underlyingSymbol='SPY',
            futFopExchange='',
            underlyingSecType='STK',
            underlyingConId=0
        )
        
        if chains:
            logger.info(f"SPY chains found: {len(chains)}")
            for i, chain in enumerate(chains):
                logger.info(f"  Chain {i}: Exchange={chain.exchange}, "
                          f"Expirations={len(chain.expirations)}")
        
    except Exception as e:
        logger.error(f"SPY test error: {e}")
    finally:
        ib.disconnect()


async def main():
    """Run all diagnostic tests."""
    print("="*60)
    print("SPX Option Chain Diagnostic")
    print("="*60)
    
    # Test SPX options
    await test_spx_options()
    
    # Test SPY for comparison
    await test_spy_comparison()
    
    print("\nDiagnostic complete!")


if __name__ == "__main__":
    asyncio.run(main())
