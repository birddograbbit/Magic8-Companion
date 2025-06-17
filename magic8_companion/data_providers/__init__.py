"""
Data providers module for Magic8-Companion.
Provides a unified interface for different data sources (IB, Yahoo, Polygon).
"""
from typing import Protocol, Dict, Any, Optional
import logging
from ..unified_config import settings

logger = logging.getLogger(__name__)


class DataProvider(Protocol):
    """Protocol for data providers."""
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain data for a symbol."""
        ...
    
    def get_spot_price(self, symbol: str) -> float:
        """Get current spot price for a symbol."""
        ...
    
    def is_connected(self) -> bool:
        """Check if provider is connected and ready."""
        ...


class IBDataProvider:
    """Interactive Brokers data provider."""
    
    def __init__(self):
        self.connected = False
        self._check_connection()
    
    def _check_connection(self):
        """Check IB connection status."""
        try:
            # In real implementation, this would check IB connection
            # For now, we'll use the existing IB client from market_analysis
            from ..modules.market_analysis import MarketAnalyzer
            # Connection check would happen here
            self.connected = True
        except Exception as e:
            logger.warning(f"IB connection failed: {e}")
            self.connected = False
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from IB."""
        if not self.connected:
            raise ConnectionError("IB not connected")
        
        # This would integrate with existing IB client
        # For now, returning structure expected by gamma analysis
        return {
            "symbol": symbol,
            "option_chain": []  # Would be populated from IB
        }
    
    def get_spot_price(self, symbol: str) -> float:
        """Get spot price from IB."""
        if not self.connected:
            raise ConnectionError("IB not connected")
        
        # Would get from IB
        return 0.0
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected


class YahooDataProvider:
    """Yahoo Finance data provider."""
    
    def __init__(self):
        self.connected = True  # Yahoo is always "connected"
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from Yahoo Finance."""
        # Would use yfinance here
        return {
            "symbol": symbol,
            "option_chain": []
        }
    
    def get_spot_price(self, symbol: str) -> float:
        """Get spot price from Yahoo."""
        # Would use yfinance
        return 0.0
    
    def is_connected(self) -> bool:
        """Yahoo is always available."""
        return True


class FileDataProvider:
    """File-based data provider for cached data."""
    
    def __init__(self, cache_path: str = "data/market_data_cache.json"):
        self.cache_path = cache_path
        self.connected = True
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from cached file."""
        import json
        import os
        
        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                return data.get(symbol, {"symbol": symbol, "option_chain": []})
        
        return {"symbol": symbol, "option_chain": []}
    
    def get_spot_price(self, symbol: str) -> float:
        """Get spot price from cache."""
        data = self.get_option_chain(symbol)
        return data.get("current_price", 0.0)
    
    def is_connected(self) -> bool:
        """File provider is always ready."""
        return True


def get_provider(provider_name: Optional[str] = None) -> DataProvider:
    """
    Get a data provider instance.
    
    Args:
        provider_name: Name of provider (ib, yahoo, file). 
                      If None, uses settings.data_provider
    
    Returns:
        DataProvider instance
    """
    if provider_name is None:
        provider_name = settings.data_provider
    
    provider_name = provider_name.lower()
    
    if provider_name == "ib":
        provider = IBDataProvider()
        # Fallback to Yahoo if IB not connected and fallback enabled
        if not provider.is_connected() and settings.ibkr_fallback_to_yahoo:
            logger.info("IB not connected, falling back to Yahoo")
            return YahooDataProvider()
        return provider
    
    elif provider_name == "yahoo":
        return YahooDataProvider()
    
    elif provider_name == "file":
        return FileDataProvider()
    
    else:
        logger.warning(f"Unknown provider {provider_name}, defaulting to file")
        return FileDataProvider()


__all__ = ["DataProvider", "get_provider", "IBDataProvider", "YahooDataProvider", "FileDataProvider"]
