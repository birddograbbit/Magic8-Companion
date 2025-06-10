"""
IBKR Market Data Module
Fetches live option chain data from Interactive Brokers TWS API.
Provides real-time data with accurate Greeks calculations.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import numpy as np
from ib_insync import IB, Stock, Option, Contract, util
import os

logger = logging.getLogger(__name__)


class IBKRMarketData:
    """Fetches real market data from Interactive Brokers."""
    
    def __init__(self):
        """Initialize the IBKR market data fetcher."""
        self.ib = IB()
        self.connected = False
        
        # Configuration from environment
        self.host = os.getenv('IBKR_HOST', '127.0.0.1')
        self.port = int(os.getenv('IBKR_PORT', '7497'))  # 7497 for paper, 7496 for live
        self.client_id = int(os.getenv('IBKR_CLIENT_ID', '1'))
        self.fallback_to_yahoo = os.getenv('IBKR_FALLBACK_TO_YAHOO', 'true').lower() == 'true'
        
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
                underlying = Contract(
                    symbol=ibkr_symbol,
                    secType='IND',
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
            await self.ib.qualifyContractsAsync(underlying)
            
            # Get current price
            ticker = await self.ib.reqTickersAsync(underlying)
            if not ticker or not ticker[0].marketPrice():
                logger.error(f"No market price available for {symbol}")
                return None
            
            current_price = float(ticker[0].marketPrice())
            
            # Get option chain data with Greeks
            option_chain_data = await self._get_option_chain_with_greeks(
                underlying, current_price
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
    
    async def _get_option_chain_with_greeks(
        self, underlying: Contract, spot_price: float
    ) -> List[Dict]:
        """Fetch option chain with real Greeks from IBKR."""
        try:
            # Get option chains
            chains = await self.ib.reqSecDefOptParamsAsync(
                underlying.symbol,
                underlying.exchange,
                underlying.secType,
                underlying.conId
            )
            
            if not chains:
                return []
            
            # Find nearest expiration (0DTE or next available)
            today = datetime.now().date()
            expirations = []
            
            for chain in chains:
                for exp in chain.expirations:
                    exp_date = datetime.strptime(exp, '%Y%m%d').date()
                    expirations.append((exp, exp_date))
            
            if not expirations:
                return []
            
            # Sort by date and get nearest
            expirations.sort(key=lambda x: x[1])
            nearest_exp, exp_date = expirations[0]
            
            # Calculate time to expiry
            days_to_exp = max(0.25, (exp_date - today).days)  # Min 0.25 for 0DTE
            time_to_expiry = days_to_exp / 365.0
            
            # Get strikes near the money (within 5% of spot)
            chain = chains[0]  # Use first chain
            strike_range = spot_price * 0.05
            min_strike = spot_price - strike_range
            max_strike = spot_price + strike_range
            
            # Filter strikes
            strikes = [float(s) for s in chain.strikes 
                      if min_strike <= float(s) <= max_strike]
            
            if not strikes:
                # If no strikes in range, get 10 closest
                all_strikes = sorted([float(s) for s in chain.strikes], 
                                   key=lambda x: abs(x - spot_price))
                strikes = all_strikes[:10]
            
            option_data = []
            
            # Fetch Greeks for each strike
            for strike in strikes:
                # Create call and put contracts
                call = Option(
                    symbol=underlying.symbol,
                    lastTradeDateOrContractMonth=nearest_exp,
                    strike=strike,
                    right='C',
                    exchange=chain.exchange,
                    currency='USD'
                )
                
                put = Option(
                    symbol=underlying.symbol,
                    lastTradeDateOrContractMonth=nearest_exp,
                    strike=strike,
                    right='P',
                    exchange=chain.exchange,
                    currency='USD'
                )
                
                # Qualify contracts
                await self.ib.qualifyContractsAsync(call, put)
                
                # Request market data with Greeks (use snapshot)
                call_ticker = self.ib.reqMktData(call, '', True, False)
                put_ticker = self.ib.reqMktData(put, '', True, False)
                
                # Wait for data
                await asyncio.sleep(1)  # Give time for Greeks to populate
                
                # Extract Greeks and market data
                call_greeks = call_ticker.modelGreeks or {}
                put_greeks = put_ticker.modelGreeks or {}
                
                option_data.append({
                    'strike': float(strike),
                    'implied_volatility': float(
                        (getattr(call_greeks, 'impliedVol', 0.15) + 
                         getattr(put_greeks, 'impliedVol', 0.15)) / 2
                    ),
                    'call_gamma': float(getattr(call_greeks, 'gamma', 0.0)),
                    'put_gamma': float(getattr(put_greeks, 'gamma', 0.0)),
                    'call_delta': float(getattr(call_greeks, 'delta', 0.0)),
                    'put_delta': float(getattr(put_greeks, 'delta', 0.0)),
                    'call_theta': float(getattr(call_greeks, 'theta', 0.0)),
                    'put_theta': float(getattr(put_greeks, 'theta', 0.0)),
                    'call_vega': float(getattr(call_greeks, 'vega', 0.0)),
                    'put_vega': float(getattr(put_greeks, 'vega', 0.0)),
                    'call_open_interest': int(call_ticker.openInterest or 0),
                    'put_open_interest': int(put_ticker.openInterest or 0),
                    'call_volume': int(call_ticker.volume or 0),
                    'put_volume': int(put_ticker.volume or 0),
                    'call_bid': float(call_ticker.bid or 0),
                    'call_ask': float(call_ticker.ask or 0),
                    'put_bid': float(put_ticker.bid or 0),
                    'put_ask': float(put_ticker.ask or 0),
                    'time_to_expiry': time_to_expiry
                })
                
                # Cancel market data subscriptions
                self.ib.cancelMktData(call_ticker)
                self.ib.cancelMktData(put_ticker)
            
            # Sort by strike
            option_data.sort(key=lambda x: x['strike'])
            
            return option_data
            
        except Exception as e:
            logger.error(f"Error fetching option chain with Greeks: {e}")
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
            else:
                print("Failed to fetch data")
    
    asyncio.run(test())
