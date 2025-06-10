"""
Real Market Data Module
Fetches live option chain data from yfinance for production testing.
Ship-fast approach: Simple, reliable, no authentication required.
"""

import yfinance as yf
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class RealMarketData:
    """Fetches real market data from yfinance."""
    
    def __init__(self):
        """Initialize the real market data fetcher."""
        self.symbol_map = {
            'SPX': '^GSPC',  # S&P 500 Index
            'QQQ': 'QQQ',    # NASDAQ 100 ETF
            'IWM': 'IWM',    # Russell 2000 ETF
            'SPY': 'SPY',    # S&P 500 ETF
            'RUT': 'IWM'     # Russell 2000 (use IWM as proxy)
        }
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch real market data for a symbol.
        
        Returns market data in the format expected by the enhanced scorer.
        """
        try:
            # Map symbol to yfinance ticker
            yf_symbol = self.symbol_map.get(symbol, symbol)
            ticker = yf.Ticker(yf_symbol)
            
            # Get current price
            info = ticker.info
            history = ticker.history(period="1d", interval="1m")
            
            if history.empty:
                logger.error(f"No price data available for {symbol}")
                return None
                
            current_price = float(history['Close'].iloc[-1])
            
            # Get options data
            option_chain_data = self._get_option_chain(ticker, current_price)
            
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
                "is_mock_data": False
            }
            
        except Exception as e:
            logger.error(f"Error fetching real market data for {symbol}: {e}")
            return None
    
    def _get_option_chain(self, ticker: yf.Ticker, spot_price: float) -> List[Dict]:
        """Fetch and format option chain data."""
        try:
            # Get available expiration dates
            expirations = ticker.options
            if not expirations:
                return []
            
            # Use the nearest expiration (0DTE or next available)
            target_date = datetime.now().date()
            nearest_exp = None
            min_diff = float('inf')
            
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                diff = abs((exp_date - target_date).days)
                if diff < min_diff:
                    min_diff = diff
                    nearest_exp = exp_str
            
            if not nearest_exp:
                return []
            
            # Calculate time to expiry
            exp_date = datetime.strptime(nearest_exp, '%Y-%m-%d').date()
            days_to_exp = max(1, (exp_date - target_date).days)
            time_to_expiry = days_to_exp / 365.0
            
            # Get option chain for nearest expiration
            opt_chain = ticker.option_chain(nearest_exp)
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            # Combine calls and puts data
            option_data = []
            
            # Get strikes near the money (within 5% of spot)
            strike_range = spot_price * 0.05
            min_strike = spot_price - strike_range
            max_strike = spot_price + strike_range
            
            # Process calls
            for _, call in calls.iterrows():
                strike = float(call['strike'])
                if min_strike <= strike <= max_strike:
                    # Calculate Greeks approximations
                    moneyness = strike / spot_price
                    gamma_est = np.exp(-((moneyness - 1) ** 2) / 0.002) * 0.002
                    
                    option_data.append({
                        'strike': strike,
                        'implied_volatility': float(call.get('impliedVolatility', 0.15)),
                        'call_gamma': gamma_est,
                        'put_gamma': 0.0,  # Will be updated from puts
                        'call_open_interest': int(call.get('openInterest', 0)),
                        'put_open_interest': 0,  # Will be updated from puts
                        'call_volume': int(call.get('volume', 0)),
                        'put_volume': 0,  # Will be updated from puts
                        'time_to_expiry': time_to_expiry
                    })
            
            # Update with puts data
            for _, put in puts.iterrows():
                strike = float(put['strike'])
                if min_strike <= strike <= max_strike:
                    # Find matching strike in option_data
                    found = False
                    for opt in option_data:
                        if opt['strike'] == strike:
                            moneyness = strike / spot_price
                            opt['put_gamma'] = np.exp(-((moneyness - 1) ** 2) / 0.002) * 0.002 * 0.8
                            opt['put_open_interest'] = int(put.get('openInterest', 0))
                            opt['put_volume'] = int(put.get('volume', 0))
                            # Average the IVs
                            put_iv = float(put.get('impliedVolatility', 0.15))
                            opt['implied_volatility'] = (opt['implied_volatility'] + put_iv) / 2
                            found = True
                            break
                    
                    # If strike not found in calls, add it
                    if not found:
                        moneyness = strike / spot_price
                        gamma_est = np.exp(-((moneyness - 1) ** 2) / 0.002) * 0.002
                        
                        option_data.append({
                            'strike': strike,
                            'implied_volatility': float(put.get('impliedVolatility', 0.15)),
                            'call_gamma': 0.0,
                            'put_gamma': gamma_est * 0.8,
                            'call_open_interest': 0,
                            'put_open_interest': int(put.get('openInterest', 0)),
                            'call_volume': 0,
                            'put_volume': int(put.get('volume', 0)),
                            'time_to_expiry': time_to_expiry
                        })
            
            # Sort by strike
            option_data.sort(key=lambda x: x['strike'])
            
            return option_data
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return []
    
    def _calculate_iv_percentile(self, option_chain: List[Dict]) -> float:
        """Calculate IV percentile from option chain."""
        if not option_chain:
            return 50.0
        
        # Get ATM IV (average of closest strikes)
        ivs = [opt['implied_volatility'] for opt in option_chain if opt['implied_volatility'] > 0]
        if not ivs:
            return 50.0
        
        atm_iv = np.median(ivs) * 100  # Convert to percentage
        
        # Map IV to percentile (simplified)
        # This is a rough approximation - in production you'd use historical data
        if atm_iv < 10:
            return 10.0
        elif atm_iv < 15:
            return 25.0
        elif atm_iv < 20:
            return 50.0
        elif atm_iv < 30:
            return 75.0
        else:
            return 90.0
    
    def _calculate_expected_range(self, option_chain: List[Dict], spot_price: float) -> float:
        """Calculate expected range from option chain."""
        if not option_chain:
            return 0.01
        
        # Use ATM straddle price to estimate expected move
        atm_strike = min(option_chain, key=lambda x: abs(x['strike'] - spot_price))
        atm_iv = atm_strike['implied_volatility']
        time_to_exp = atm_strike.get('time_to_expiry', 1/365)
        
        # Expected move = IV * sqrt(time) * spot
        expected_move = atm_iv * np.sqrt(time_to_exp) * spot_price
        expected_range_pct = expected_move / spot_price
        
        return round(expected_range_pct, 4)
    
    def _determine_gamma_environment(self, option_chain: List[Dict], spot_price: float) -> str:
        """Determine gamma environment from option chain."""
        if not option_chain:
            return "Unknown"
        
        # Calculate total gamma exposure
        total_gamma = sum(opt['call_gamma'] + opt['put_gamma'] for opt in option_chain)
        
        # Get ATM data
        atm_option = min(option_chain, key=lambda x: abs(x['strike'] - spot_price))
        atm_iv = atm_option['implied_volatility'] * 100
        
        # Determine environment based on gamma and IV
        if total_gamma > 0.05 and atm_iv < 20:
            return "Low volatility, high gamma"
        elif total_gamma < 0.02 and atm_iv > 30:
            return "High volatility, low gamma"
        elif atm_iv < 25:
            return "Range-bound, moderate gamma"
        else:
            return "Directional, variable gamma"


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        fetcher = RealMarketData()
        data = await fetcher.get_market_data("SPY")
        if data:
            print(f"Symbol: {data['symbol']}")
            print(f"Spot Price: ${data['spot_price']:.2f}")
            print(f"IV Percentile: {data['iv_percentile']}")
            print(f"Expected Range: {data['expected_range_pct']:.2%}")
            print(f"Gamma Environment: {data['gamma_environment']}")
            print(f"Option Chain Strikes: {len(data['option_chain'])}")
        else:
            print("Failed to fetch data")
    
    asyncio.run(test())
