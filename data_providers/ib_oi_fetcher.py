"""
IBKR Open Interest Fetcher
Handles streaming OI data which cannot be obtained via snapshots
"""
import math
import time
from typing import Dict, List, Optional
from ib_insync import IB, Contract, Option
import logging

logger = logging.getLogger(__name__)

# OI requires streaming, not snapshots
OI_GENERIC_TICKS = "100,101"  # 100=call OI, 101=put OI

class IBOpenInterestFetcher:
    def __init__(self, ib: IB):
        self.ib = ib
        self.oi_timeout = 2.0  # seconds to wait for OI data
        
    def get_oi_data_streaming(self, contracts: List[Contract], timeout: float = None) -> Dict[int, int]:
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
            for contract in contracts:
                ticker = self.ib.reqMktData(
                    contract, 
                    genericTickList=OI_GENERIC_TICKS, 
                    snapshot=False
                )
                streaming_tickers.append(ticker)
            
            # Wait for data to populate
            self.ib.sleep(timeout)
            
            # Extract OI data
            for ticker in streaming_tickers:
                if ticker.contract and ticker.contract.conId:
                    oi_value = 0
                    
                    # Extract OI based on option type
                    if hasattr(ticker.contract, 'right'):
                        if ticker.contract.right == "C":
                            oi_value = (
                                getattr(ticker, 'callOpenInterest', 0) or 
                                getattr(ticker, 'openInterest', 0) or 0
                            )
                        else:
                            oi_value = (
                                getattr(ticker, 'putOpenInterest', 0) or 
                                getattr(ticker, 'openInterest', 0) or 0
                            )
                    
                    if oi_value and not math.isnan(oi_value):
                        oi_data[ticker.contract.conId] = int(oi_value)
            
            logger.info(f"Successfully retrieved OI data for {len(oi_data)} contracts")
            
        except Exception as e:
            logger.error(f"Error getting OI data via streaming: {e}")
        finally:
            # Cancel all streaming subscriptions
            for ticker in streaming_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except:
                    pass
        
        return oi_data
        
    def enhance_options_with_oi(self, options: List[Dict], symbol: str = "SPX") -> List[Dict]:
        """
        Enhance existing options data with OI information
        """
        # Create Option contracts from the data
        contracts = []
        option_map = {}  # Map contract to original option dict
        
        for opt in options:
            try:
                contract = Option(
                    symbol, 
                    opt['expiry'], 
                    opt['strike'], 
                    opt['right'],
                    exchange="SMART",
                    tradingClass="SPXW" if symbol == "SPX" else symbol
                )
                contracts.append(contract)
                option_map[id(contract)] = opt
            except Exception as e:
                logger.error(f"Error creating contract for option: {e}")
                
        if not contracts:
            logger.warning("No valid contracts to fetch OI for")
            return options
            
        # Qualify contracts
        qualified = self.ib.qualifyContracts(*contracts)
        
        # Get OI data
        oi_data = self.get_oi_data_streaming(qualified)
        
        # Map OI back to options
        for contract in qualified:
            if contract.conId in oi_data:
                opt = option_map.get(id(contract))
                if opt:
                    opt['open_interest'] = oi_data[contract.conId]
                    logger.debug(f"Added OI {oi_data[contract.conId]} to {contract.strike} {contract.right}")
                    
        return options
