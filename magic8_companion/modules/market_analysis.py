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
from ..data_providers import DataProvider

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Market analyzer supporting IB (primary) and Yahoo Finance (fallback)."""
    
    def __init__(self, data_provider: Optional[DataProvider] = None):
        # FIX: Use effective_use_mock_data to respect complexity mode
        self.use_mock_data = settings.effective_use_mock_data
        self.data_provider = data_provider  # Use the shared data provider
        self.iv_history = {}  # Store historical IV for percentile calculation
        self.cache_dir = Path('data')
        
        # Log which data source we're using
        logger.info(f"MarketAnalyzer initialized: use_mock_data={self.use_mock_data}, provider={settings.market_data_provider}, complexity={settings.system_complexity}")
        
        # Path to cache file
        self.cache_file = self.cache_dir / "market_data_cache.json"
        self.cache_max_age = 300  # seconds
    
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
                "source": market_data.get("data_provider", "unknown"),
                "option_chain": option_chain_data or []
            }
            
            # Write cache
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
                
            logger.debug(f"Market data cache updated for {symbol}")
            
        except Exception as e:
            logger.error(f"Error writing market data cache: {e}")

    def _check_cache(self, symbol: str):
        """Check if valid cache data exists for symbol"""
        try:
            if not self.cache_file.exists():
                logger.debug("Cache file not found - ensure Magic8-Companion is running")
                return None

            with open(self.cache_file, 'r') as f:
                try:
                    cache = json.load(f)
                except Exception as e:
                    logger.error(f"Error parsing cache file: {e}")
                    return None

            if 'timestamp' not in cache or 'data' not in cache:
                logger.debug("Cache missing required fields")
                return None

            if symbol not in cache['data']:
                logger.debug(f"Symbol {symbol} not found in cache")
                return None

            try:
                cache_time = datetime.fromisoformat(cache['timestamp'])
            except Exception:
                logger.debug("Invalid cache timestamp")
                return None

            age_seconds = (datetime.now() - cache_time).total_seconds()

            if age_seconds > self.cache_max_age:
                logger.debug(f"Cache too old: {age_seconds:.1f}s > {self.cache_max_age}s")
                return None

            source = cache.get('source', 'unknown')
            logger.info(f"Using cached {source.upper()} data for {symbol} (age: {age_seconds:.1f}s)")

            return cache['data'][symbol]

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None
        
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol."""
        logger.debug(f"Analyzing market conditions for {symbol}")

        # Return cached data if valid and not using mock data
        if not self.use_mock_data:
            cached = self._check_cache(symbol)
            if cached:
                return cached

        if self.use_mock_data:
            market_data = self._get_mock_market_data(symbol)
        else:
            market_data = await self._get_live_market_data(symbol)
        
        # Already written to cache in the data fetching methods
        return market_data
    
    async def _get_live_market_data(self, symbol: str) -> Optional[Dict]:
        """Get live market data using the shared data provider."""
        if not self.data_provider:
            logger.error("No data provider available")
            logger.info("Falling back to mock data")
            return self._get_mock_market_data(symbol)
        
        try:
            # Get option chain from data provider
            option_chain_result = await self.data_provider.get_option_chain(symbol)
            
            if not option_chain_result or 'option_chain' not in option_chain_result:
                raise ValueError(f"No option chain data available for {symbol}")
            
            current_price = option_chain_result.get('current_price', 0)
            option_chain = option_chain_result.get('option_chain', [])
            
            # Calculate average IV from ATM options
            call_ivs = []
            put_ivs = []
            
            for opt in option_chain:
                strike = opt['strike']
                # ATM is within 1% of current price
                if abs(strike - current_price) / current_price < 0.01:
                    if opt.get('call_iv'):
                        call_ivs.append(opt['call_iv'])
                    if opt.get('put_iv'):
                        put_ivs.append(opt['put_iv'])
            
            if not call_ivs and not put_ivs:
                # Use all options if no ATM found
                call_ivs = [opt['call_iv'] for opt in option_chain if opt.get('call_iv')]
                put_ivs = [opt['put_iv'] for opt in option_chain if opt.get('put_iv')]
            
            if not call_ivs and not put_ivs:
                raise ValueError(f"No IV data available for {symbol}")
            
            # Average of call and put IVs (already in decimal form from provider)
            all_ivs = call_ivs + put_ivs
            iv = np.mean(all_ivs) * 100  # Convert to percentage
            
            # Store IV for historical tracking
            self._store_iv_history(symbol, iv)
            
            # Calculate IV percentile based on historical data
            iv_percentile = self._calculate_iv_percentile(symbol, iv)
            
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
                "implied_vol": round(iv, 1),
                "analysis_timestamp": datetime.now().isoformat(),
                "is_mock_data": False,
                "data_provider": settings.market_data_provider
            }
            
            # Write to cache with option chain data
            self._write_market_data_cache(symbol, market_data, option_chain)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            logger.info("Falling back to mock data")
            return self._get_mock_market_data(symbol)
    
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
