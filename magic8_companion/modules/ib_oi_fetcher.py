"""
IBKR Open Interest Fetcher
Handles streaming OI data which cannot be obtained via snapshots
"""
import math
import asyncio
from typing import Dict, List, Optional
from ib_async import IB, Contract, Option
import logging

logger = logging.getLogger(__name__)

# OI requires streaming, not snapshots
OI_GENERIC_TICKS = "100,101"  # 100=call OI, 101=put OI

class IBOpenInterestFetcher:
    def __init__(self, ib: IB):
        self.ib = ib
        self.oi_timeout = 2.0  # seconds to wait for OI data
        
    async def get_oi_data_streaming(self, contracts: List[Contract], timeout: float = None) -> Dict[int, int]:
        """
        Get Open Interest data using brief streaming approach.
        Returns {conId: oi_value} mapping.
        """
        if timeout is None:
            timeout = self.oi_timeout
            
        logger.info(f"Attempting to get OI data via streaming for {len(contracts)} contracts...")
        oi_data = {}
        streaming_tickers = []
        
        try:
            # Start streaming requests for OI
            # NOTE: ib_async uses reqMktData, not reqMktDataAsync
            for contract in contracts:
                ticker = self.ib.reqMktData(
                    contract, 
                    genericTickList=OI_GENERIC_TICKS, 
                    snapshot=False
                )
                streaming_tickers.append(ticker)
            
            # Wait for data to populate
            await asyncio.sleep(timeout)
            
            # Extract OI data
            for ticker in streaming_tickers:
                if ticker.contract and ticker.contract.conId:
                    oi_value = 0
                    
                    # Extract OI based on option type
                    if hasattr(ticker.contract, 'right'):
                        if ticker.contract.right == "C":
                            # Check various possible attribute names
                            oi_value = (
                                getattr(ticker, 'callOpenInterest', 0) or 
                                getattr(ticker, 'openInterest', 0) or 
                                getattr(ticker, 'lastGreeks', {}).get('openInterest', 0) or 0
                            )
                        else:
                            oi_value = (
                                getattr(ticker, 'putOpenInterest', 0) or 
                                getattr(ticker, 'openInterest', 0) or 
                                getattr(ticker, 'lastGreeks', {}).get('openInterest', 0) or 0
                            )
                    
                    # Log what we're seeing for debugging
                    if hasattr(ticker, '__dict__'):
                        logger.debug(f"Ticker attributes for {ticker.contract.strike} {ticker.contract.right}: {list(ticker.__dict__.keys())}")
                    
                    if oi_value and not math.isnan(oi_value):
                        oi_data[ticker.contract.conId] = int(oi_value)
                        logger.info(f"Got OI {oi_value} for {ticker.contract.strike} {ticker.contract.right}")
            
            logger.info(f"Successfully retrieved OI data for {len(oi_data)} contracts")
            
        except Exception as e:
            logger.error(f"Error getting OI data via streaming: {e}", exc_info=True)
        finally:
            # Cancel all streaming subscriptions
            for ticker in streaming_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except:
                    pass
        
        return oi_data
        
    async def enhance_options_with_oi(self, options: List[Dict], contracts: List[Contract]) -> List[Dict]:
        """
        Enhance existing options data with OI information
        """
        # Create mapping of conId to option dict
        conid_to_option = {}
        for opt, contract in zip(options, contracts):
            if contract.conId:
                conid_to_option[contract.conId] = opt
        
        # Get OI data
        oi_data = await self.get_oi_data_streaming(contracts)
        
        # Map OI back to options
        for conid, oi_value in oi_data.items():
            if conid in conid_to_option:
                conid_to_option[conid]['open_interest'] = oi_value
                logger.debug(f"Added OI {oi_value} to contract {conid}")
                    
        return options
