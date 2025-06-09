"""
Market analyzer for Magic8-Companion.
Supports both mock data and live market data via Yahoo Finance.
"""
import logging
from typing import Dict, Optional
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

from ..config import settings

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Market analyzer supporting both mock and live data."""
    
    def __init__(self):
        self.use_mock_data = settings.use_mock_data
        self.provider = settings.market_data_provider
        
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol."""
        logger.debug(f"Analyzing market conditions for {symbol}")
        
        if self.use_mock_data:
            return self._get_mock_market_data(symbol)
        else:
            return await self._get_live_market_data(symbol)
    
    async def _get_live_market_data(self, symbol: str) -> Optional[Dict]:
        """Get live market data from configured provider."""
        try:
            if self.provider == "yahoo":
                return self._get_yahoo_market_data(symbol)
            elif self.provider == "ib":
                # TODO: Implement IB data fetching
                logger.warning("IB data provider not implemented yet, using Yahoo")
                return self._get_yahoo_market_data(symbol)
            elif self.provider == "polygon":
                # TODO: Implement Polygon data fetching
                logger.warning("Polygon data provider not implemented yet, using Yahoo")
                return self._get_yahoo_market_data(symbol)
            else:
                logger.error(f"Unknown market data provider: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            logger.info("Falling back to mock data")
            return self._get_mock_market_data(symbol)
    
    def _get_yahoo_market_data(self, symbol: str) -> Dict:
        """Get market data from Yahoo Finance."""
        # For index symbols, Yahoo uses ^ prefix
        yahoo_symbol = f"^{symbol}" if symbol in ["SPX", "RUT"] else symbol
        
        try:
            # Get ticker object
            ticker = yf.Ticker(yahoo_symbol)
            
            # Get current price and historical data
            info = ticker.info
            hist = ticker.history(period="30d")
            
            # Calculate realized volatility (30-day)
            returns = hist['Close'].pct_change().dropna()
            realized_vol = returns.std() * np.sqrt(252) * 100  # Annualized
            
            # Get options chain for IV calculation
            try:
                # Get nearest expiration
                expirations = ticker.options
                if expirations:
                    nearest_exp = expirations[0]
                    opt_chain = ticker.option_chain(nearest_exp)
                    
                    # Calculate approximate IV from ATM options
                    current_price = hist['Close'].iloc[-1]
                    calls = opt_chain.calls
                    puts = opt_chain.puts
                    
                    # Find ATM strike
                    strikes = calls['strike'].values
                    atm_strike = strikes[np.abs(strikes - current_price).argmin()]
                    
                    # Get ATM IV (average of call and put)
                    atm_call_iv = calls[calls['strike'] == atm_strike]['impliedVolatility'].iloc[0]
                    atm_put_iv = puts[puts['strike'] == atm_strike]['impliedVolatility'].iloc[0]
                    iv = (atm_call_iv + atm_put_iv) / 2 * 100
                    
                    # Calculate IV percentile (simplified - compare to realized vol)
                    iv_percentile = min(100, (iv / realized_vol) * 50)
                else:
                    iv = realized_vol
                    iv_percentile = 50  # Default to middle
            except:
                # Fallback if options data not available
                iv = realized_vol
                iv_percentile = 50
            
            # Calculate expected daily range
            expected_range_pct = iv / 100 / np.sqrt(252)  # Daily move
            
            # Determine gamma environment
            gamma_env = self._determine_gamma_environment(iv_percentile, expected_range_pct)
            
            return {
                "symbol": symbol,
                "iv_percentile": round(iv_percentile, 1),
                "expected_range_pct": round(expected_range_pct, 4),
                "gamma_environment": gamma_env,
                "current_price": round(current_price, 2),
                "realized_vol": round(realized_vol, 1),
                "implied_vol": round(iv, 1),
                "analysis_timestamp": datetime.now().isoformat(),
                "is_mock_data": False,
                "data_provider": "yahoo"
            }
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {e}")
            raise
    
    def _get_mock_market_data(self, symbol: str) -> Dict:
        """Generate mock market data for testing."""
        # Simulate different market conditions based on symbol
        if symbol == "SPX":
            base_iv = 65.0
            base_range = 0.008
        elif symbol == "SPY":
            base_iv = 62.0
            base_range = 0.007
        elif symbol == "QQQ":
            base_iv = 70.0
            base_range = 0.012
        elif symbol == "RUT":
            base_iv = 75.0
            base_range = 0.015
        else:
            base_iv = settings.mock_iv_percentile
            base_range = settings.mock_expected_range_pct
        
        # Simulate time-based variations
        hour = datetime.now().hour
        
        # Make conditions more volatile in afternoon
        time_multiplier = 1.0 + (hour - 12) * 0.1 if hour > 12 else 1.0
        
        return {
            "symbol": symbol,
            "iv_percentile": base_iv * time_multiplier,
            "expected_range_pct": base_range * time_multiplier,
            "gamma_environment": self._determine_gamma_environment(base_iv, base_range),
            "analysis_timestamp": datetime.now().isoformat(),
            "is_mock_data": True
        }
    
    def _determine_gamma_environment(self, iv_percentile: float, range_pct: float) -> str:
        """Determine gamma environment description."""
        if iv_percentile < 30 and range_pct < 0.005:
            return "Low volatility, high gamma"
        elif iv_percentile > 70 and range_pct > 0.015:
            return "High volatility, low gamma"
        elif range_pct < 0.008:
            return "Range-bound, moderate gamma"
        else:
            return "Directional, variable gamma"
