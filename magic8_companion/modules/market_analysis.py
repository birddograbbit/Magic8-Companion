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
import json
from pathlib import Path

from ..unified_config import settings
from ..modules.ib_client_manager import IBClientManager

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Market analyzer supporting IB (primary) and Yahoo Finance (fallback)."""
    
    def __init__(self):
        # FIX: Use effective_use_mock_data to respect complexity mode
        self.use_mock_data = settings.effective_use_mock_data
        self.provider = settings.market_data_provider
        self.ib_client_manager = None
        self.iv_history = {}  # Store historical IV for percentile calculation
        self.cache_dir = Path('data')
        
        # Log which data source we're using
        logger.info(f"MarketAnalyzer initialized: use_mock_data={self.use_mock_data}, provider={self.provider}, complexity={settings.system_complexity}")
        
        # Initialize IB client manager if configured and not using mock data
        if self.provider == "ib" and not self.use_mock_data:
            try:
                self.ib_client_manager = IBClientManager()
                logger.info("IB client manager initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize IB client manager: {e}")
                self.ib_client_manager = None
    
    def _write_market_data_cache(self, symbol: str, market_data: Dict, option_chain_data: Optional[List] = None):
        """Write market data to cache for sharing with other modules."""
        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(exist_ok=True)
            
            cache_file = self.cache_dir / 'market_data_cache.json'
            
            # Read existing cache or create new
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
            else:
                cache = {"timestamp": None, "source": None, "data": {}}
            
            # Update cache
            cache["timestamp"] = datetime.now().isoformat()
            cache["source"] = market_data.get("data_provider", "unknown")
            
            # Store market data
            cache["data"][symbol] = {
                "spot_price": market_data.get("current_price", 0),
                "implied_vol": market_data.get("implied_vol", 20),
                "iv_percentile": market_data.get("iv_percentile", 50),
                "last_updated": datetime.now().isoformat(),
                "option_chain": option_chain_data or []
            }
            
            # Write cache
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
                
            logger.debug(f"Market data cache updated for {symbol}")
            
        except Exception as e:
            logger.error(f"Error writing market data cache: {e}")
        
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol."""
        logger.debug(f"Analyzing market conditions for {symbol}")
        
        if self.use_mock_data:
            market_data = self._get_mock_market_data(symbol)
        else:
            market_data = await self._get_live_market_data(symbol)
        
        # Already written to cache in the data fetching methods
        return market_data
    
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
            
            # Get ATM options data (includes IV) - but we need more strikes!
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
            
            # Build comprehensive option chain data for MLOptionTrading
            # Organize by strike to consolidate call/put data
            strikes_data = {}
            
            for opt in atm_options:
                strike = opt.get("strike", 0)
                if strike not in strikes_data:
                    strikes_data[strike] = {
                        "strike": strike,
                        "call_oi": 0,
                        "put_oi": 0,
                        "call_iv": 0.20,
                        "put_iv": 0.20,
                        "call_bid": 0.0,
                        "call_ask": 0.0,
                        "put_bid": 0.0,
                        "put_ask": 0.0,
                        "call_gamma": 0.0,
                        "put_gamma": 0.0,
                        "call_delta": 0.0,
                        "put_delta": 0.0,
                        "call_volume": 0,
                        "put_volume": 0,
                        "dte": 0  # 0DTE for MLOptionTrading
                    }
                
                # Fill in the data based on option type
                if opt.get("right") == "C":
                    strikes_data[strike]["call_oi"] = opt.get("open_interest", 0) or 0
                    strikes_data[strike]["call_iv"] = opt.get("implied_volatility", 0.20) or 0.20
                    strikes_data[strike]["call_bid"] = opt.get("bid", 0.0) or 0.0
                    strikes_data[strike]["call_ask"] = opt.get("ask", 0.0) or 0.0
                    # Add Greeks if available from IBKR
                    strikes_data[strike]["call_gamma"] = 0.01  # Placeholder - would need to get from IBKR modelGreeks
                    strikes_data[strike]["call_delta"] = 0.5 if strike >= current_price else 0.3  # Rough approximation
                else:  # Put
                    strikes_data[strike]["put_oi"] = opt.get("open_interest", 0) or 0
                    strikes_data[strike]["put_iv"] = opt.get("implied_volatility", 0.20) or 0.20
                    strikes_data[strike]["put_bid"] = opt.get("bid", 0.0) or 0.0
                    strikes_data[strike]["put_ask"] = opt.get("ask", 0.0) or 0.0
                    # Add Greeks if available from IBKR
                    strikes_data[strike]["put_gamma"] = 0.01  # Placeholder - would need to get from IBKR modelGreeks
                    strikes_data[strike]["put_delta"] = -0.5 if strike <= current_price else -0.3  # Rough approximation
            
            # Convert to list sorted by strike
            option_chain_data = list(strikes_data.values())
            option_chain_data.sort(key=lambda x: x["strike"])
            
            # Log what we're caching
            logger.info(f"Caching {len(option_chain_data)} strikes for {symbol} option chain")
            
            market_data = {
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
            
            # Write to cache with option chain data
            self._write_market_data_cache(symbol, market_data, option_chain_data)
            
            return market_data
            
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
            option_chain_data = []
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
                    
                    # Prepare comprehensive option chain data for cache
                    for _, call_row in calls.iterrows():
                        put_row = puts[puts['strike'] == call_row['strike']]
                        option_chain_data.append({
                            "strike": call_row['strike'],
                            "call_oi": int(call_row.get('openInterest', 0)),
                            "put_oi": int(put_row['openInterest'].iloc[0]) if not put_row.empty else 0,
                            "call_iv": call_row.get('impliedVolatility', 0.20),
                            "put_iv": put_row['impliedVolatility'].iloc[0] if not put_row.empty else 0.20,
                            "call_bid": call_row.get('bid', 0.0),
                            "call_ask": call_row.get('ask', 0.0),
                            "put_bid": put_row['bid'].iloc[0] if not put_row.empty else 0.0,
                            "put_ask": put_row['ask'].iloc[0] if not put_row.empty else 0.0,
                            "call_gamma": 0.01,  # Yahoo doesn't provide Greeks
                            "put_gamma": 0.01,
                            "call_delta": 0.5 if call_row['strike'] >= current_price else 0.3,
                            "put_delta": -0.5 if call_row['strike'] <= current_price else -0.3,
                            "call_volume": int(call_row.get('volume', 0)),
                            "put_volume": int(put_row['volume'].iloc[0]) if not put_row.empty else 0,
                            "dte": 0  # Approximate for 0DTE
                        })
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
            
            market_data = {
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
            
            # Write to cache with option chain data
            self._write_market_data_cache(symbol, market_data, option_chain_data)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo data for {symbol}: {e}")
            raise
    
    def _get_mock_market_data(self, symbol: str) -> Dict:
        """Generate mock market data for testing."""
        # Simulate different market conditions based on symbol
        if symbol == "SPX":
            base_iv = 15.0
            base_range = 0.008
            base_price = 5950
        elif symbol == "SPY":
            base_iv = 18.0
            base_range = 0.007
            base_price = 595
        elif symbol == "QQQ":
            base_iv = 22.0
            base_range = 0.012
            base_price = 490
        elif symbol == "RUT":
            base_iv = 25.0
            base_range = 0.015
            base_price = 2200
        else:
            base_iv = settings.mock_iv_percentile
            base_range = settings.mock_expected_range_pct
            base_price = 100
        
        # Simulate time-based variations
        hour = datetime.now().hour
        
        # Make conditions more volatile in afternoon
        time_multiplier = 1.0 + (hour - 12) * 0.1 if hour > 12 else 1.0
        
        iv = base_iv * time_multiplier
        iv_percentile = min(100, iv * 2)  # Simple mock percentile
        
        # Generate more comprehensive mock option chain
        strikes = [base_price + i * 5 for i in range(-20, 21)]  # More strikes
        option_chain_data = []
        for strike in strikes:
            distance = abs(strike - base_price) / base_price
            base_oi = int(10000 * np.exp(-distance * 20))
            option_chain_data.append({
                "strike": strike,
                "call_oi": base_oi,
                "put_oi": base_oi,
                "call_iv": base_iv / 100 + distance * 0.1,
                "put_iv": base_iv / 100 + distance * 0.1,
                "call_bid": max(0, base_price - strike) * 0.95 if strike < base_price else 0.5,
                "call_ask": max(0, base_price - strike) * 1.05 if strike < base_price else 0.6,
                "put_bid": max(0, strike - base_price) * 0.95 if strike > base_price else 0.5,
                "put_ask": max(0, strike - base_price) * 1.05 if strike > base_price else 0.6,
                "call_gamma": 0.01 * np.exp(-distance * 10),
                "put_gamma": 0.01 * np.exp(-distance * 10),
                "call_delta": 0.5 - distance * 2 if strike >= base_price else 0.5 + distance * 2,
                "put_delta": -0.5 + distance * 2 if strike <= base_price else -0.5 - distance * 2,
                "call_volume": base_oi // 10,
                "put_volume": base_oi // 10,
                "dte": 0
            })
        
        market_data = {
            "symbol": symbol,
            "iv_percentile": iv_percentile,
            "expected_range_pct": base_range * time_multiplier,
            "gamma_environment": self._determine_gamma_environment(iv_percentile, base_range),
            "current_price": base_price,
            "implied_vol": iv,
            "analysis_timestamp": datetime.now().isoformat(),
            "is_mock_data": True,
            "data_provider": "mock"
        }
        
        # Write to cache with option chain data
        self._write_market_data_cache(symbol, market_data, option_chain_data)
        
        return market_data
    
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
