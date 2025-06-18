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
        self.oi_timeout = 5.0  # Increased from 3.0 for better reliability
        self.batch_size = 20   # Process contracts in batches to avoid overwhelming IB
        
    async def get_oi_data_streaming(self, contracts: List[Contract], timeout: float = None) -> Dict[int, int]:
        """
        Get Open Interest data using brief streaming approach.
        Now processes contracts in batches for better reliability.
        Returns {conId: oi_value} mapping.
        """
        if timeout is None:
            timeout = self.oi_timeout
            
        logger.info(f"Attempting to get OI data via streaming for {len(contracts)} contracts...")
        oi_data = {}
        
        # Process in batches to avoid overwhelming IB
        for batch_start in range(0, len(contracts), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(contracts))
            batch = contracts[batch_start:batch_end]
            
            logger.debug(f"Processing batch {batch_start//self.batch_size + 1}: contracts {batch_start+1}-{batch_end}")
            batch_oi = await self._get_batch_oi_data(batch, timeout)
            oi_data.update(batch_oi)
            
            # Small delay between batches to avoid rate limiting
            if batch_end < len(contracts):
                await asyncio.sleep(0.5)
        
        logger.info(f"Successfully retrieved OI data for {len(oi_data)} contracts out of {len(contracts)}")
        
        # If we got very few results, log a warning
        success_rate = len(oi_data) / len(contracts) if contracts else 0
        if success_rate < 0.5 and len(contracts) > 0:
            logger.warning(f"Low OI success rate ({success_rate:.1%}). This might be due to:")
            logger.warning("  - Market closed (OI updates during market hours)")
            logger.warning("  - Some strikes may not have OI data")
            logger.warning("  - Consider increasing timeout or reducing batch size")
        
        return oi_data
        
    async def _get_batch_oi_data(self, batch: List[Contract], timeout: float) -> Dict[int, int]:
        """
        Get OI data for a batch of contracts.
        """
        oi_data = {}
        streaming_tickers = []
        
        try:
            # Start streaming requests for OI
            for contract in batch:
                ticker = self.ib.reqMktData(
                    contract, 
                    genericTickList=OI_GENERIC_TICKS, 
                    snapshot=False,
                    regulatorySnapshot=False
                )
                streaming_tickers.append(ticker)
            
            # Wait for data to populate
            await asyncio.sleep(timeout)
            
            # Extract OI data
            for ticker in streaming_tickers:
                if ticker.contract and ticker.contract.conId:
                    oi_value = None
                    
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
                            if not math.isnan(oi_float) and oi_float >= 0:  # Allow 0 OI
                                oi_data[ticker.contract.conId] = int(oi_float)
                                if oi_float > 0:  # Only log non-zero OI
                                    logger.debug(f"Got OI {int(oi_float)} for {ticker.contract.strike} {ticker.contract.right}")
                        except (ValueError, TypeError):
                            logger.debug(f"Invalid OI value {oi_value} for {ticker.contract.strike} {ticker.contract.right}")
            
        except Exception as e:
            logger.error(f"Error getting OI data for batch: {e}", exc_info=True)
        finally:
            # Cancel all streaming subscriptions for this batch
            for ticker in streaming_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except Exception as e:
                    logger.debug(f"Error canceling market data: {e}")
        
        return oi_data
        
    async def enhance_options_with_oi(self, options: List[Dict], contracts: List[Contract]) -> List[Dict]:
        """
        Enhance existing options data with OI information.
        Prioritizes near-ATM strikes for better performance.
        """
        if not contracts:
            logger.warning("No contracts provided for OI enhancement")
            return options
            
        # Create mapping of conId to option dict
        conid_to_option = {}
        for opt, contract in zip(options, contracts):
            if contract.conId:
                conid_to_option[contract.conId] = opt
        
        # Sort contracts by distance from ATM for priority processing
        # (Near ATM strikes are more important for gamma calculations)
        spot_price = options[0].get('underlying_price_at_fetch', 0) if options else 0
        if spot_price > 0:
            sorted_contracts = sorted(contracts, 
                                    key=lambda c: abs(c.strike - spot_price) if hasattr(c, 'strike') else float('inf'))
        else:
            sorted_contracts = contracts
        
        # Get OI data
        oi_data = await self.get_oi_data_streaming(sorted_contracts)
        
        # Map OI back to options
        oi_success_count = 0
        for conid, oi_value in oi_data.items():
            if conid in conid_to_option:
                conid_to_option[conid]['open_interest'] = oi_value
                oi_success_count += 1
                
        if oi_success_count > 0:
            logger.info(f"Enhanced {oi_success_count} options with OI data out of {len(options)} total")
        else:
            logger.warning(f"Could not enhance any options with OI data. This may be normal outside market hours.")
                    
        return options
    
    def set_timeout(self, timeout: float):
        """Allow dynamic timeout adjustment"""
        self.oi_timeout = timeout
        logger.info(f"OI timeout set to {timeout} seconds")
        
    def set_batch_size(self, batch_size: int):
        """Allow dynamic batch size adjustment"""
        self.batch_size = batch_size
        logger.info(f"OI batch size set to {batch_size}")
