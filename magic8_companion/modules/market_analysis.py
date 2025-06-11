"""
Market analyzer for Magic8-Companion.
Prioritizes IB data for real-time options information, falls back to Yahoo Finance.
"""
import logging
from typing import Dict, Optional, List
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import asyncio
from collections import deque

from ..config import settings
from ..modules.ib_client_manager import IBClientManager

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Market analyzer supporting IB (primary) and Yahoo Finance (fallback)."""
    
    def __init__(self):
        self.use_mock_data = settings.use_mock_data
        self.provider = settings.market_data_provider
        self.ib_client_manager = None
        self.iv_history = {}  # Store historical IV for percentile calculation
        
        # Initialize IB client manager if configured
        if self.provider == "ib" or not self.use_mock_data:
            try:
                self.ib_client_manager = IBClientManager()
            except Exception as e:
                logger.warning(f"Failed to initialize IB client manager: {e}")
                self.ib_client_manager = None
        
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol."""
        logger.debug(f"Analyzing market conditions for {symbol}")
        
        if self.use_mock_data:
            return self._get_mock_market_data(symbol)
        else:
            return await self._get_live_market_data(symbol)
    
    async def _get_live_market_data(self, symbol: str) -> Optional[Dict]:
        """Get live market data, prioritizing IB then falling back to other providers."""
        # Always try IB first if available
        if self.ib_client_manager:
            try:
                return await self._get_ib_market_data(symbol)
            except Exception as e:
                logger.warning(f"IB data fetch failed for {symbol}: {e}")
                logger.info("Falling back to alternative data provider")
        
        # Fallback logic
        try:
            if self.provider == "yahoo" or self.provider == "ib":
                return await self._get_yahoo_market_data(symbol)
            elif self.provider == "polygon":
                logger.warning("Polygon data provider not implemented yet, using Yahoo")
                return await self._get_yahoo_market_data(symbol)
            else:
                logger.error(f"Unknown market data provider: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            logger.info("Falling back to mock data")
            return self._get_mock_market_data(symbol)
    
    async def _get_ib_market_data(self, symbol: str) -> Dict:
        """Get market data from Interactive Brokers."""
        try:
            # Get the singleton IB client
            ib_client = await self.ib_client_manager.get_client()
            if not ib_client:
                raise ConnectionError("Failed to get IB client from manager")
            
            # Ensure connection
            await ib_client._ensure_connected()
            
            # Get ATM options data (includes IV)
            atm_options = await ib_client.get_atm_options([symbol], days_to_expiry=0)
            
            if not atm_options:
                raise ValueError(f"No ATM options data available for {symbol}")
            
            # Extract data from ATM options
            current_price = atm_options[0].get('underlying_price_at_fetch', 0)
            
            # Calculate average IV from ATM options
            call_ivs = [opt['implied_volatility'] for opt in atm_options 
                       if opt['right'] == 'C' and opt['implied_volatility'] is not None]
            put_ivs = [opt['implied_volatility'] for opt in atm_options 
                      if opt['right'] == 'P' and opt['implied_volatility'] is not None]
            
            if not call_ivs and not put_ivs:
                raise ValueError(f"No IV data available for {symbol}")
            
            # Average of ATM call and put IVs
            all_ivs = call_ivs + put_ivs
            iv = np.mean(all_ivs) * 100  # Convert to percentage
            
            # Store IV for historical tracking
            self._store_iv_history(symbol, iv)
            
            # Calculate IV percentile based on historical data
            iv_percentile = self._calculate_iv_percentile(symbol, iv)
            
            # Calculate expected daily range
            expected_range_pct = iv / 100 / np.sqrt(252)  # Daily move
            
            # Determine gamma environment based on ATM bid-ask spreads
            atm_call = next((opt for opt in atm_options if opt['right'] == 'C' and 
                            abs(opt['strike'] - current_price) / current_price < 0.01), None)
            
            if atm_call and atm_call['bid'] and atm_call['ask']:
                spread_pct = (atm_call['ask'] - atm_call['bid']) / current_price
                if spread_pct < 0.001:  # Tight spread
                    gamma_env = "High gamma, liquid markets"
                else:
                    gamma_env = "Moderate gamma environment"
            else:
                gamma_env = self._determine_gamma_environment(iv_percentile, expected_range_pct)
            
            return {
                "symbol": symbol,
                "iv_percentile": round(iv_percentile, 1),
                "expected_range_pct": round(expected_range_pct, 4),
                "gamma_environment": gamma_env,
                "current_price": round(current_price, 2),
                "implied_vol": round(iv, 1),
                "atm_options_count": len(atm_options),
                "analysis_timestamp": datetime.now().isoformat(),
                "is_mock_data": False,
                "data_provider": "ib"
            }
            
        except Exception as e:
            logger.error(f"Error fetching IB data for {symbol}: {e}")
            raise
    
    def _store_iv_history(self, symbol: str, iv: float):
        """Store IV value for historical percentile calculation."""
        if symbol not in self.iv_history:
            self.iv_history[symbol] = deque(maxlen=252)  # Store 1 year of daily values
        self.iv_history[symbol].append(iv)
    
    def _calculate_iv_percentile(self, symbol: str, current_iv: float) -> float:
        """Calculate IV percentile based on historical data."""
        if symbol not in self.iv_history or len(self.iv_history[symbol]) < 20:
            # Not enough history, use a simple heuristic
            # Low IV: < 20, Medium: 20-50, High: > 50
            if current_iv < 20:
                return 25.0  # Low percentile
            elif current_iv < 50:
                return 50.0  # Medium percentile
            else:
                return 75.0  # High percentile
        
        # Calculate actual percentile
        history = list(self.iv_history[symbol])
        return (sum(1 for iv in history if iv <= current_iv) / len(history)) * 100
    
    async def _get_yahoo_market_data(self, symbol: str) -> Dict:
        """Get market data from Yahoo Finance."""
        # For index symbols, Yahoo uses ^ prefix
        yahoo_symbol = f"^{symbol}" if symbol in ["SPX", "RUT"] else symbol
        
        try:
            # Get ticker object
            ticker = yf.Ticker(yahoo_symbol)

            # Get current price and historical data
            info = await asyncio.to_thread(lambda: ticker.info)
            hist = await asyncio.to_thread(ticker.history, period="30d")
            
            # Calculate realized volatility (30-day)
            returns = hist['Close'].pct_change().dropna()
            realized_vol = returns.std() * np.sqrt(252) * 100  # Annualized
            
            # Get options chain for IV calculation
            try:
                # Get nearest expiration
                expirations = await asyncio.to_thread(lambda: ticker.options)
                if expirations:
                    nearest_exp = expirations[0]
                    opt_chain = await asyncio.to_thread(ticker.option_chain, nearest_exp)
                    
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
                    
                    # Store and calculate IV percentile
                    self._store_iv_history(symbol, iv)
                    iv_percentile = self._calculate_iv_percentile(symbol, iv)
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
            base_iv = 15.0
            base_range = 0.008
        elif symbol == "SPY":
            base_iv = 18.0
            base_range = 0.007
        elif symbol == "QQQ":
            base_iv = 22.0
            base_range = 0.012
        elif symbol == "RUT":
            base_iv = 25.0
            base_range = 0.015
        else:
            base_iv = settings.mock_iv_percentile
            base_range = settings.mock_expected_range_pct
        
        # Simulate time-based variations
        hour = datetime.now().hour
        
        # Make conditions more volatile in afternoon
        time_multiplier = 1.0 + (hour - 12) * 0.1 if hour > 12 else 1.0
        
        iv = base_iv * time_multiplier
        iv_percentile = min(100, iv * 2)  # Simple mock percentile
        
        return {
            "symbol": symbol,
            "iv_percentile": iv_percentile,
            "expected_range_pct": base_range * time_multiplier,
            "gamma_environment": self._determine_gamma_environment(iv_percentile, base_range),
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
