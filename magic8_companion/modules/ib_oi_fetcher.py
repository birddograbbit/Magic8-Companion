"""
IBKR Open Interest Fetcher
Handles streaming OI data which cannot be obtained via snapshots
"""
import math
import asyncio
from typing import Dict, List, Optional
from ib_async import IB, Contract, Option, Ticker
import logging

logger = logging.getLogger(__name__)

# OI requires streaming, not snapshots
OI_GENERIC_TICKS = "100,101"  # 100=call OI, 101=put OI

class IBOpenInterestFetcher:
    def __init__(self, ib: IB):
        self.ib = ib
        self.oi_timeout = 3.0  # seconds to wait for OI data (increased from 2.0)
        
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
            # In ib_async, reqMktData returns a Ticker immediately
            for contract in contracts:
                ticker = self.ib.reqMktData(
                    contract, 
                    genericTickList=OI_GENERIC_TICKS, 
                    snapshot=False,
                    regulatorySnapshot=False
                )
                streaming_tickers.append(ticker)
            
            # Wait for data to populate
            logger.debug(f"Waiting {timeout} seconds for OI data to stream...")
            await asyncio.sleep(timeout)
            
            # Extract OI data
            found_oi_count = 0
            for ticker in streaming_tickers:
                if ticker.contract and ticker.contract.conId:
                    oi_value = None
                    
                    # Log ticker state for debugging
                    if logger.isEnabledFor(logging.DEBUG):
                        attrs = [attr for attr in dir(ticker) if not attr.startswith('_')]
                        logger.debug(f"Ticker attributes for {ticker.contract.strike} {ticker.contract.right}: {attrs}")
                        
                        # Log actual values of OI-related attributes
                        for attr in ['callOpenInterest', 'putOpenInterest', 'openInterest']:
                            if hasattr(ticker, attr):
                                val = getattr(ticker, attr)
                                if val is not None:
                                    logger.debug(f"  {attr}: {val}")
                    
                    # Try multiple ways to get OI based on ib_async ticker structure
                    if ticker.contract.right == "C":
                        # For calls, check these in order
                        oi_value = (
                            getattr(ticker, 'callOpenInterest', None) or
                            getattr(ticker, 'openInterest', None)
                        )
                    else:  # Put
                        # For puts, check these in order
                        oi_value = (
                            getattr(ticker, 'putOpenInterest', None) or
                            getattr(ticker, 'openInterest', None)
                        )
                    
                    # Convert and validate
                    if oi_value is not None:
                        try:
                            oi_float = float(oi_value)
                            if not math.isnan(oi_float) and oi_float > 0:
                                oi_data[ticker.contract.conId] = int(oi_float)
                                found_oi_count += 1
                                logger.debug(f"Got OI {int(oi_float)} for {ticker.contract.strike} {ticker.contract.right}")
                        except (ValueError, TypeError):
                            logger.debug(f"Invalid OI value {oi_value} for {ticker.contract.strike} {ticker.contract.right}")
            
            logger.info(f"Successfully retrieved OI data for {found_oi_count} contracts out of {len(contracts)}")
            
            # If we got no OI data at all, it might be a market hours issue
            if found_oi_count == 0:
                logger.warning("No OI data retrieved. This might be normal outside market hours or for certain symbols.")
            
        except Exception as e:
            logger.error(f"Error getting OI data via streaming: {e}", exc_info=True)
        finally:
            # Cancel all streaming subscriptions
            logger.debug("Canceling all streaming subscriptions...")
            for ticker in streaming_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except Exception as e:
                    logger.debug(f"Error canceling market data for {ticker.contract}: {e}")
        
        return oi_data
        
    async def enhance_options_with_oi(self, options: List[Dict], contracts: List[Contract]) -> List[Dict]:
        """
        Enhance existing options data with OI information
        """
        if not contracts:
            logger.warning("No contracts provided for OI enhancement")
            return options
            
        # Create mapping of conId to option dict
        conid_to_option = {}
        for opt, contract in zip(options, contracts):
            if contract.conId:
                conid_to_option[contract.conId] = opt
        
        # Get OI data
        oi_data = await self.get_oi_data_streaming(contracts)
        
        # Map OI back to options
        oi_success_count = 0
        for conid, oi_value in oi_data.items():
            if conid in conid_to_option:
                conid_to_option[conid]['open_interest'] = oi_value
                oi_success_count += 1
                
        if oi_success_count > 0:
            logger.info(f"Enhanced {oi_success_count} options with OI data out of {len(options)} total")
        else:
            logger.warning(f"Could not enhance any options with OI data. This may be normal for SPX outside market hours.")
                    
        return options
