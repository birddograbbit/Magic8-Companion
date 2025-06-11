"""
IBKR Market Data Module
Fetches live option chain data from Interactive Brokers TWS API.
Provides real-time data with accurate Greeks calculations.
Enhanced with strike limits and better error handling for 0DTE trading.
"""

import logging
import asyncio
import math
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import numpy as np
from ib_async import IB, Stock, Option, Contract, Index, util, Ticker
from magic8_companion.config import settings

logger = logging.getLogger(__name__)

# Generic tick constants based on working script
# These work with snapshots
SNAPSHOT_GENERIC_TICKS = ",".join([
    "106",  # option implied vol
    "107",  # option delta
    "108",  # option gamma
    "109",  # option vega
    "110",  # option theta
    "13",   # last volume
    "104",  # bid/ask sizes
])

# These require streaming
OI_GENERIC_TICKS = ",".join([
    "100",  # call OI
    "101",  # put OI
])

# Constants for managing IBKR limits
MAX_STRIKES_ABOVE_ATM = 25  # Maximum strikes above ATM
MAX_STRIKES_BELOW_ATM = 25  # Maximum strikes below ATM
MAX_CONCURRENT_TICKERS = 90  # Stay well below IBKR's limit of ~100
BATCH_SIZE = 20  # Process options in batches


class IBKRMarketData:
    """Fetches real market data from Interactive Brokers."""
    
    def __init__(self):
        """Initialize the IBKR market data fetcher."""
        self.ib = IB()
        self.connected = False
        
        # Configuration from settings
        self.host = settings.ibkr_host
        self.port = settings.ibkr_port
        self.client_id = settings.ibkr_client_id
        self.fallback_to_yahoo = settings.ibkr_fallback_to_yahoo
        
        # Symbol mapping for IBKR
        self.symbol_map = {
            'SPX': 'SPX',    # S&P 500 Index
            'QQQ': 'QQQ',    # NASDAQ 100 ETF
            'IWM': 'IWM',    # Russell 2000 ETF
            'SPY': 'SPY',    # S&P 500 ETF
            'RUT': 'RUT'     # Russell 2000 Index
        }
        
        # Exchange mapping
        self.exchange_map = {
            'SPX': 'CBOE',
            'RUT': 'RUSSELL',
            'QQQ': 'SMART',
            'IWM': 'SMART',
            'SPY': 'SMART'
        }
        
        # Trading class preferences for 0DTE
        self.trading_class_map = {
            'SPX': 'SPXW',  # Use weekly options for 0DTE
            'RUT': 'RUT',
            'QQQ': 'QQQ',
            'IWM': 'IWM',
            'SPY': 'SPY'
        }
        
        # OI streaming configuration
        self.oi_streaming_timeout = 2.0  # seconds to wait for OI data
    
    async def connect(self) -> bool:
        """Connect to TWS/IB Gateway."""
        try:
            if not self.connected:
                await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
                self.connected = True
                logger.info(f"Connected to IBKR TWS at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from TWS/IB Gateway."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR TWS")
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch real market data for a symbol from IBKR.
        
        Returns market data in the format expected by the enhanced scorer.
        """
        try:
            # Ensure connection
            if not self.connected:
                if not await self.connect():
                    if self.fallback_to_yahoo:
                        logger.warning("Falling back to Yahoo Finance")
                        from .real_market_data import RealMarketData
                        yahoo_fetcher = RealMarketData()
                        return await yahoo_fetcher.get_market_data(symbol)
                    return None
            
            # Get underlying contract
            ibkr_symbol = self.symbol_map.get(symbol, symbol)
            exchange = self.exchange_map.get(symbol, 'SMART')
            
            # Create appropriate contract
            if symbol in ['SPX', 'RUT']:
                # Index options
                underlying = Index(
                    symbol=ibkr_symbol,
                    exchange=exchange,
                    currency='USD'
                )
            else:
                # Stock/ETF options
                underlying = Stock(
                    symbol=ibkr_symbol,
                    exchange=exchange,
                    currency='USD'
                )
            
            # Qualify the contract
            contracts = await self.ib.qualifyContractsAsync(underlying)
            if not contracts:
                logger.error(f"Failed to qualify contract for {symbol}")
                return None
            underlying = contracts[0]
            logger.debug(f"Qualified {symbol}: conId={underlying.conId}")
            
            # Get current price
            ticker = await self.ib.reqTickersAsync(underlying)
            if not ticker or not ticker[0].marketPrice():
                logger.error(f"No market price available for {symbol}")
                return None
            
            current_price = float(ticker[0].marketPrice())
            
            # Get option chain data with Greeks
            option_chain_data = await self._get_option_chain_with_greeks(
                underlying, current_price, symbol
            )
            
            if not option_chain_data:
                logger.error(f"No option chain data available for {symbol}")
                return None
            
            # Calculate market metrics
            iv_percentile = self._calculate_iv_percentile(option_chain_data)
            expected_range = self._calculate_expected_range(option_chain_data, current_price)
            gamma_env = self._determine_gamma_environment(option_chain_data, current_price)
            
            return {
                "symbol": symbol,
                "spot_price": current_price,
                "iv_percentile": iv_percentile,
                "expected_range_pct": expected_range,
                "gamma_environment": gamma_env,
                "time_to_expiry": option_chain_data[0].get('time_to_expiry', 1/365),
                "option_chain": option_chain_data,
                "analysis_timestamp": datetime.now().isoformat(),
                "is_mock_data": False,
                "data_source": "IBKR"
            }
            
        except Exception as e:
            logger.error(f"Error fetching IBKR market data for {symbol}: {e}")
            if self.fallback_to_yahoo:
                logger.warning("Falling back to Yahoo Finance due to error")
                from .real_market_data import RealMarketData
                yahoo_fetcher = RealMarketData()
                return await yahoo_fetcher.get_market_data(symbol)
            return None
    
    async def _get_oi_streaming_batch(self, contracts: List[Contract], batch_size: int = 40) -> Dict[int, int]:
        """
        Get Open Interest data using streaming approach in batches.
        Processes contracts in smaller batches to avoid hitting ticker limits.
        """
        oi_data = {}
        
        # Process in batches
        for i in range(0, len(contracts), batch_size):
            batch = contracts[i:i + batch_size]
            logger.debug(f"Processing OI batch {i//batch_size + 1}/{(len(contracts) + batch_size - 1)//batch_size}")
            
            streaming_tickers = []
            try:
                # Start streaming requests for this batch
                for contract in batch:
                    try:
                        ticker = self.ib.reqMktData(
                            contract, 
                            genericTickList=OI_GENERIC_TICKS, 
                            snapshot=False
                        )
                        streaming_tickers.append((ticker, contract))
                    except Exception as e:
                        logger.warning(f"Failed to request OI data for {contract.strike} {contract.right}: {e}")
                
                # Wait for data to populate
                await asyncio.sleep(self.oi_streaming_timeout)
                
                # Extract OI data
                for ticker, contract in streaming_tickers:
                    if ticker.contract and ticker.contract.conId:
                        oi_value = 0
                        
                        # Extract OI based on option type
                        if ticker.contract.right == "C":
                            oi_value = getattr(ticker, 'callOpenInterest', 0) or getattr(ticker, 'openInterest', 0) or 0
                        else:
                            oi_value = getattr(ticker, 'putOpenInterest', 0) or getattr(ticker, 'openInterest', 0) or 0
                        
                        # Handle NaN values
                        if oi_value and not math.isnan(oi_value):
                            oi_data[ticker.contract.conId] = int(oi_value)
                
            except Exception as e:
                logger.warning(f"Error in OI batch processing: {e}")
            finally:
                # Cancel all streaming subscriptions for this batch
                for ticker, _ in streaming_tickers:
                    try:
                        self.ib.cancelMktData(ticker.contract)
                    except Exception as e:
                        logger.debug(f"Error canceling market data: {e}")
        
        return oi_data
    
    async def _get_option_chain_with_greeks(
        self, underlying: Contract, spot_price: float, original_symbol: str
    ) -> List[Dict]:
        """
        Fetch option chain with real Greeks from IBKR.
        Enhanced with strike limits and better error handling.
        """
        try:
            chains = []
            
            # Use the contract's actual conId
            logger.info(f"Fetching option chains for {original_symbol} (conId={underlying.conId})")
            
            # Get all available chains
            chains = await self.ib.reqSecDefOptParamsAsync(
                underlyingSymbol=underlying.symbol,
                futFopExchange='',
                underlyingSecType=underlying.secType,
                underlyingConId=underlying.conId
            )
            
            if not chains:
                logger.warning(f"No option chains found for {original_symbol}")
                return []
            
            # Filter for preferred trading class (e.g., SPXW for SPX 0DTE)
            preferred_class = self.trading_class_map.get(original_symbol)
            filtered_chains = []
            
            for chain in chains:
                # Log chain details
                logger.debug(f"Found chain: Exchange={chain.exchange}, TradingClass={chain.tradingClass}, "
                           f"Multiplier={chain.multiplier}, Expirations={len(chain.expirations)}, "
                           f"Strikes={len(chain.strikes)}")
                
                # Prefer SPXW for SPX 0DTE trading
                if preferred_class and hasattr(chain, 'tradingClass'):
                    if chain.tradingClass == preferred_class:
                        filtered_chains.append(chain)
                else:
                    filtered_chains.append(chain)
            
            # Use filtered chains if available, otherwise use all
            chains_to_use = filtered_chains if filtered_chains else chains
            logger.info(f"Using {len(chains_to_use)} chain(s) for {original_symbol}")
            
            # Find nearest expiration (0DTE or next available)
            today = datetime.now().date()
            expirations = []
            
            for chain in chains_to_use:
                for exp in chain.expirations:
                    exp_date = datetime.strptime(exp, '%Y%m%d').date()
                    expirations.append((exp, exp_date, chain))
            
            if not expirations:
                logger.warning("No expirations found in option chains")
                return []
            
            # Sort by date and get nearest
            expirations.sort(key=lambda x: x[1])
            nearest_exp, exp_date, selected_chain = expirations[0]
            
            logger.info(f"Selected expiration: {nearest_exp} ({exp_date}) on {selected_chain.exchange} "
                       f"with tradingClass={selected_chain.tradingClass}")
            
            # Calculate time to expiry
            days_to_exp = max(0.25, (exp_date - today).days)  # Min 0.25 for 0DTE
            time_to_expiry = days_to_exp / 365.0
            
            # Get ATM strike
            all_strikes = sorted([float(s) for s in selected_chain.strikes])
            atm_strike = min(all_strikes, key=lambda x: abs(x - spot_price))
            atm_index = all_strikes.index(atm_strike)
            
            # Select limited strikes around ATM to avoid hitting ticker limits
            strikes_below = all_strikes[max(0, atm_index - MAX_STRIKES_BELOW_ATM):atm_index]
            strikes_above = all_strikes[atm_index + 1:min(len(all_strikes), atm_index + 1 + MAX_STRIKES_ABOVE_ATM)]
            strikes = strikes_below + [atm_strike] + strikes_above
            
            logger.info(f"Selected {len(strikes)} strikes around ATM {atm_strike}: "
                       f"range [{strikes[0]} - {strikes[-1]}]")
            
            # Build list of all option contracts
            all_contracts = []
            contract_map = {}  # Map conId to (strike, right)
            
            # Use the symbol from the underlying contract
            option_symbol = underlying.symbol
            
            # First, create and qualify all contracts
            for strike in strikes:
                # Create call and put contracts
                call = Option(
                    symbol=option_symbol,
                    lastTradeDateOrContractMonth=nearest_exp,
                    strike=strike,
                    right='C',
                    exchange=selected_chain.exchange,
                    currency='USD'
                )
                
                put = Option(
                    symbol=option_symbol,
                    lastTradeDateOrContractMonth=nearest_exp,
                    strike=strike,
                    right='P',
                    exchange=selected_chain.exchange,
                    currency='USD'
                )
                
                # Set trading class
                if hasattr(selected_chain, 'tradingClass') and selected_chain.tradingClass:
                    call.tradingClass = selected_chain.tradingClass
                    put.tradingClass = selected_chain.tradingClass
                
                # Qualify contracts with better error handling
                try:
                    qualified_call = await self.ib.qualifyContractsAsync(call)
                    if qualified_call and qualified_call[0].conId:
                        call = qualified_call[0]
                        all_contracts.append(call)
                        contract_map[call.conId] = (strike, 'C')
                    else:
                        logger.warning(f"Failed to qualify call for strike {strike}")
                except Exception as e:
                    logger.warning(f"Error qualifying call for strike {strike}: {e}")
                
                try:
                    qualified_put = await self.ib.qualifyContractsAsync(put)
                    if qualified_put and qualified_put[0].conId:
                        put = qualified_put[0]
                        all_contracts.append(put)
                        contract_map[put.conId] = (strike, 'P')
                    else:
                        logger.warning(f"Failed to qualify put for strike {strike}")
                except Exception as e:
                    logger.warning(f"Error qualifying put for strike {strike}: {e}")
            
            logger.info(f"Successfully qualified {len(all_contracts)} option contracts")
            
            if not all_contracts:
                logger.error("No contracts were successfully qualified")
                return []
            
            # Get OI data via streaming in batches
            oi_data = await self._get_oi_streaming_batch(all_contracts, batch_size=BATCH_SIZE)
            
            # Process contracts in batches for snapshot data
            option_data = []
            processed_tickers = []
            
            for i in range(0, len(all_contracts), BATCH_SIZE):
                batch = all_contracts[i:i + BATCH_SIZE]
                logger.debug(f"Processing snapshot batch {i//BATCH_SIZE + 1}/{(len(all_contracts) + BATCH_SIZE - 1)//BATCH_SIZE}")
                
                batch_tickers = []
                
                # Request market data for this batch
                for contract in batch:
                    try:
                        ticker = self.ib.reqMktData(
                            contract, 
                            genericTickList=SNAPSHOT_GENERIC_TICKS,
                            snapshot=True, 
                            regulatorySnapshot=False
                        )
                        batch_tickers.append((ticker, contract))
                        processed_tickers.append(ticker)
                    except Exception as e:
                        logger.warning(f"Failed to request data for {contract.strike} {contract.right}: {e}")
                
                # Wait for snapshot data
                await asyncio.sleep(1.0)
                
                # Process batch results
                for ticker, contract in batch_tickers:
                    try:
                        if ticker.marketPrice() is not None and contract.conId in contract_map:
                            strike, right = contract_map[contract.conId]
                            
                            # Get OI from streaming data
                            oi_value = oi_data.get(contract.conId, 0)
                            
                            # Extract Greeks
                            greeks = ticker.modelGreeks or {}
                            
                            # Find or create option data entry for this strike
                            strike_data = next((d for d in option_data if d['strike'] == strike), None)
                            if not strike_data:
                                strike_data = {
                                    'strike': float(strike),
                                    'time_to_expiry': time_to_expiry,
                                    'implied_volatility': 0.15,  # Default
                                    'call_gamma': 0.0, 'put_gamma': 0.0,
                                    'call_delta': 0.0, 'put_delta': 0.0,
                                    'call_theta': 0.0, 'put_theta': 0.0,
                                    'call_vega': 0.0, 'put_vega': 0.0,
                                    'call_open_interest': 0, 'put_open_interest': 0,
                                    'call_volume': 0, 'put_volume': 0,
                                    'call_bid': 0.0, 'call_ask': 0.0,
                                    'put_bid': 0.0, 'put_ask': 0.0,
                                }
                                option_data.append(strike_data)
                            
                            # Update with contract-specific data
                            if right == 'C':
                                strike_data['call_bid'] = float(ticker.bid or 0)
                                strike_data['call_ask'] = float(ticker.ask or 0)
                                strike_data['call_volume'] = int(ticker.volume or 0)
                                strike_data['call_open_interest'] = oi_value
                                strike_data['call_delta'] = float(getattr(greeks, 'delta', 0.0))
                                strike_data['call_gamma'] = float(getattr(greeks, 'gamma', 0.0))
                                strike_data['call_theta'] = float(getattr(greeks, 'theta', 0.0))
                                strike_data['call_vega'] = float(getattr(greeks, 'vega', 0.0))
                                if hasattr(greeks, 'impliedVol'):
                                    strike_data['_call_iv'] = float(greeks.impliedVol)
                            else:
                                strike_data['put_bid'] = float(ticker.bid or 0)
                                strike_data['put_ask'] = float(ticker.ask or 0)
                                strike_data['put_volume'] = int(ticker.volume or 0)
                                strike_data['put_open_interest'] = oi_value
                                strike_data['put_delta'] = float(getattr(greeks, 'delta', 0.0))
                                strike_data['put_gamma'] = float(getattr(greeks, 'gamma', 0.0))
                                strike_data['put_theta'] = float(getattr(greeks, 'theta', 0.0))
                                strike_data['put_vega'] = float(getattr(greeks, 'vega', 0.0))
                                if hasattr(greeks, 'impliedVol'):
                                    strike_data['_put_iv'] = float(greeks.impliedVol)
                    
                    except Exception as e:
                        logger.warning(f"Error processing ticker data: {e}")
            
            # Clean up all market data subscriptions
            logger.debug("Canceling all market data subscriptions...")
            for ticker in processed_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except Exception as e:
                    logger.debug(f"Error canceling subscription: {e}")
            
            # Calculate average IV for each strike
            for data in option_data:
                call_iv = data.pop('_call_iv', 0.15)
                put_iv = data.pop('_put_iv', 0.15)
                data['implied_volatility'] = (call_iv + put_iv) / 2
            
            # Sort by strike
            option_data.sort(key=lambda x: x['strike'])
            
            logger.info(f"Retrieved option data for {len(option_data)} strikes")
            if oi_data:
                logger.info(f"Successfully retrieved OI data for {len(oi_data)} contracts")
            
            return option_data
            
        except Exception as e:
            logger.error(f"Error fetching option chain with Greeks: {e}", exc_info=True)
            return []
    
    def _calculate_iv_percentile(self, option_chain: List[Dict]) -> float:
        """Calculate IV percentile from option chain."""
        if not option_chain:
            return 50.0
        
        # Get ATM IV
        ivs = [opt['implied_volatility'] for opt in option_chain 
               if opt['implied_volatility'] > 0]
        if not ivs:
            return 50.0
        
        atm_iv = np.median(ivs) * 100  # Convert to percentage
        
        # More sophisticated IV percentile calculation
        # In production, you'd compare to historical IV data from IBKR
        if atm_iv < 10:
            return 5.0
        elif atm_iv < 12:
            return 15.0
        elif atm_iv < 15:
            return 30.0
        elif atm_iv < 20:
            return 50.0
        elif atm_iv < 25:
            return 70.0
        elif atm_iv < 35:
            return 85.0
        else:
            return 95.0
    
    def _calculate_expected_range(self, option_chain: List[Dict], spot_price: float) -> float:
        """Calculate expected range from option chain using real Greeks."""
        if not option_chain:
            return 0.01
        
        # Find ATM option
        atm_option = min(option_chain, key=lambda x: abs(x['strike'] - spot_price))
        
        # Use actual IV and time to calculate expected move
        atm_iv = atm_option['implied_volatility']
        time_to_exp = atm_option.get('time_to_expiry', 1/365)
        
        # Expected move formula with real IV
        expected_move = atm_iv * np.sqrt(time_to_exp) * spot_price
        expected_range_pct = expected_move / spot_price
        
        return round(expected_range_pct, 4)
    
    def _determine_gamma_environment(self, option_chain: List[Dict], spot_price: float) -> str:
        """Determine gamma environment using real Greeks from IBKR."""
        if not option_chain:
            return "Unknown"
        
        # Calculate total gamma exposure using real Greeks
        total_gamma = sum(
            abs(opt['call_gamma']) * opt['call_open_interest'] * 100 +
            abs(opt['put_gamma']) * opt['put_open_interest'] * 100
            for opt in option_chain
        )
        
        # Normalize by spot price
        normalized_gamma = total_gamma / (spot_price ** 2)
        
        # Get ATM data
        atm_option = min(option_chain, key=lambda x: abs(x['strike'] - spot_price))
        atm_iv = atm_option['implied_volatility'] * 100
        
        # Determine environment based on real gamma and IV
        if normalized_gamma > 1000 and atm_iv < 20:
            return "Low volatility, high gamma"
        elif normalized_gamma < 100 and atm_iv > 30:
            return "High volatility, low gamma"
        elif atm_iv < 25 and 100 <= normalized_gamma <= 1000:
            return "Range-bound, moderate gamma"
        else:
            return "Directional, variable gamma"


# Context manager for automatic connection handling
class IBKRConnection:
    """Context manager for IBKR connections."""
    
    def __init__(self, market_data: IBKRMarketData):
        self.market_data = market_data
    
    async def __aenter__(self):
        await self.market_data.connect()
        return self.market_data
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.market_data.disconnect()


# Example usage
if __name__ == "__main__":
    async def test():
        ibkr = IBKRMarketData()
        
        # Use context manager for automatic connection handling
        async with IBKRConnection(ibkr) as market_data:
            data = await market_data.get_market_data("SPX")
            if data:
                print(f"Symbol: {data['symbol']}")
                print(f"Spot Price: ${data['spot_price']:.2f}")
                print(f"IV Percentile: {data['iv_percentile']}")
                print(f"Expected Range: {data['expected_range_pct']:.2%}")
                print(f"Gamma Environment: {data['gamma_environment']}")
                print(f"Data Source: {data['data_source']}")
                print(f"Option Chain Strikes: {len(data['option_chain'])}")
                
                # Show sample Greeks
                if data['option_chain']:
                    sample = data['option_chain'][len(data['option_chain'])//2]
                    print(f"\nSample Greeks for strike {sample['strike']}:")
                    print(f"  Call Delta: {sample['call_delta']:.4f}")
                    print(f"  Call Gamma: {sample['call_gamma']:.6f}")
                    print(f"  Call Theta: {sample['call_theta']:.4f}")
                    print(f"  Call Vega: {sample['call_vega']:.4f}")
                    print(f"  Call OI: {sample['call_open_interest']}")
                    print(f"  Put OI: {sample['put_open_interest']}")
            else:
                print("Failed to fetch data")
    
    asyncio.run(test())
