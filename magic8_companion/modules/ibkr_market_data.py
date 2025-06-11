"""
IBKR Market Data Module
Fetches live option chain data from Interactive Brokers TWS API.
Provides real-time data with accurate Greeks calculations.
"""

import logging
import asyncio
import math  # Added for NaN handling
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
    
    async def _get_oi_streaming(self, contracts: List[Contract]) -> Dict[int, int]:
        """
        Get Open Interest data using streaming approach.
        Based on the working script's implementation.
        Returns {conId: oi_value} mapping.
        """
        logger.debug(f"Getting OI data via streaming for {len(contracts)} contracts...")
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
            await asyncio.sleep(self.oi_streaming_timeout)
            
            # Extract OI data
            for ticker in streaming_tickers:
                if ticker.contract and ticker.contract.conId:
                    oi_value = 0
                    
                    # Extract OI based on option type
                    if ticker.contract.right == "C":
                        # Try callOpenInterest first, then general openInterest
                        oi_value = getattr(ticker, 'callOpenInterest', 0) or getattr(ticker, 'openInterest', 0) or 0
                    else:
                        # Try putOpenInterest first, then general openInterest
                        oi_value = getattr(ticker, 'putOpenInterest', 0) or getattr(ticker, 'openInterest', 0) or 0
                    
                    # Handle NaN values
                    if oi_value and not math.isnan(oi_value):
                        oi_data[ticker.contract.conId] = int(oi_value)
            
            logger.debug(f"Successfully retrieved OI data for {len(oi_data)} contracts")
            
        except Exception as e:
            logger.warning(f"Error getting OI data via streaming: {e}")
        finally:
            # Cancel all streaming subscriptions
            for ticker in streaming_tickers:
                try:
                    self.ib.cancelMktData(ticker.contract)
                except:
                    pass
        
        return oi_data
    
    async def _get_option_chain_with_greeks(
        self, underlying: Contract, spot_price: float, original_symbol: str
    ) -> List[Dict]:
        """
        Fetch option chain with real Greeks from IBKR.
        Uses two-phase approach: snapshot for prices/Greeks, streaming for OI.
        """
        try:
            chains = []
            
            # Use the contract's actual conId instead of passing separately
            logger.info(f"Fetching option chains for {original_symbol} (conId={underlying.conId})")
            
            # For all symbols, use the standard approach with the actual contract
            chains = await self.ib.reqSecDefOptParamsAsync(
                underlyingSymbol=underlying.symbol,
                futFopExchange='',  # Empty string for all exchanges
                underlyingSecType=underlying.secType,
                underlyingConId=underlying.conId  # Use the actual conId
            )
            
            if not chains:
                logger.warning(f"No option chains found for {original_symbol}")
                return []
            
            # Log chain details for debugging
            logger.info(f"Found {len(chains)} option chain(s) for {original_symbol}")
            for i, chain in enumerate(chains):
                logger.debug(f"Chain {i}: Exchange={chain.exchange}, TradingClass={chain.tradingClass}, "
                           f"Multiplier={chain.multiplier}, Expirations={len(chain.expirations)}, "
                           f"Strikes={len(chain.strikes)}")
            
            # Find nearest expiration (0DTE or next available)
            today = datetime.now().date()
            expirations = []
            
            for chain in chains:
                for exp in chain.expirations:
                    exp_date = datetime.strptime(exp, '%Y%m%d').date()
                    expirations.append((exp, exp_date, chain))
            
            if not expirations:
                logger.warning("No expirations found in option chains")
                return []
            
            # Sort by date and get nearest
            expirations.sort(key=lambda x: x[1])
            nearest_exp, exp_date, selected_chain = expirations[0]
            
            logger.info(f"Selected expiration: {nearest_exp} ({exp_date}) on {selected_chain.exchange}")
            
            # Calculate time to expiry
            days_to_exp = max(0.25, (exp_date - today).days)  # Min 0.25 for 0DTE
            time_to_expiry = days_to_exp / 365.0
            
            # Get strikes near the money (within 5% of spot)
            strike_range = spot_price * 0.05
            min_strike = spot_price - strike_range
            max_strike = spot_price + strike_range
            
            # Filter strikes
            strikes = [float(s) for s in selected_chain.strikes 
                      if min_strike <= float(s) <= max_strike]
            
            if not strikes:
                # If no strikes in range, get 10 closest
                all_strikes = sorted([float(s) for s in selected_chain.strikes], 
                                   key=lambda x: abs(x - spot_price))
                strikes = all_strikes[:10]
            
            logger.info(f"Selected {len(strikes)} strikes near {spot_price}")
            
            # Build list of all option contracts for OI streaming
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
                
                # Set trading class if it's different from symbol (e.g., SPXW for SPX)
                if hasattr(selected_chain, 'tradingClass') and selected_chain.tradingClass:
                    call.tradingClass = selected_chain.tradingClass
                    put.tradingClass = selected_chain.tradingClass
                
                # Qualify contracts
                try:
                    qualified_call = await self.ib.qualifyContractsAsync(call)
                    qualified_put = await self.ib.qualifyContractsAsync(put)
                    
                    if qualified_call and qualified_put:
                        call = qualified_call[0]
                        put = qualified_put[0]
                        all_contracts.extend([call, put])
                        contract_map[call.conId] = (strike, 'C')
                        contract_map[put.conId] = (strike, 'P')
                except Exception as e:
                    logger.warning(f"Error qualifying contracts for strike {strike}: {e}")
                    continue
            
            # Get OI data via streaming for all contracts at once
            oi_data = await self._get_oi_streaming(all_contracts)
            
            # Now get snapshot data for each contract with price/Greeks
            option_data = []
            
            for contract in all_contracts:
                try:
                    # Request market data with Greeks (use snapshot, no OI ticks)
                    ticker = self.ib.reqMktData(
                        contract, 
                        genericTickList=SNAPSHOT_GENERIC_TICKS,  # No OI ticks
                        snapshot=True, 
                        regulatorySnapshot=False
                    )
                    
                    # Wait for snapshot data
                    await asyncio.sleep(0.5)
                    
                    # Only process if we have valid price data
                    if ticker.marketPrice() is not None:
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
                        else:
                            strike_data['put_bid'] = float(ticker.bid or 0)
                            strike_data['put_ask'] = float(ticker.ask or 0)
                            strike_data['put_volume'] = int(ticker.volume or 0)
                            strike_data['put_open_interest'] = oi_value
                            strike_data['put_delta'] = float(getattr(greeks, 'delta', 0.0))
                            strike_data['put_gamma'] = float(getattr(greeks, 'gamma', 0.0))
                            strike_data['put_theta'] = float(getattr(greeks, 'theta', 0.0))
                            strike_data['put_vega'] = float(getattr(greeks, 'vega', 0.0))
                        
                        # Update IV (average of call and put)
                        if right == 'C' and hasattr(greeks, 'impliedVol'):
                            call_iv = float(getattr(greeks, 'impliedVol', 0.15))
                            put_data = next((d for d in option_data if d['strike'] == strike), {})
                            put_iv = put_data.get('_put_iv', 0.15)
                            strike_data['implied_volatility'] = (call_iv + put_iv) / 2
                            strike_data['_call_iv'] = call_iv
                        elif right == 'P' and hasattr(greeks, 'impliedVol'):
                            put_iv = float(getattr(greeks, 'impliedVol', 0.15))
                            strike_data['_put_iv'] = put_iv
                            call_iv = strike_data.get('_call_iv', 0.15)
                            strike_data['implied_volatility'] = (call_iv + put_iv) / 2
                    
                    # Cancel market data subscription
                    self.ib.cancelMktData(ticker)
                    
                except Exception as e:
                    logger.warning(f"Error getting data for {contract.strike} {contract.right}: {e}")
                    continue
            
            # Clean up temporary IV fields and sort by strike
            for data in option_data:
                data.pop('_call_iv', None)
                data.pop('_put_iv', None)
            
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
            data = await market_data.get_market_data("SPY")
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
