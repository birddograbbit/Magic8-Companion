"""
Data providers module for Magic8-Companion.
Provides a unified interface for different data sources (IB, Yahoo, Polygon).
"""

from typing import Protocol, Dict, Any, Optional
import logging
import asyncio
from ..unified_config import settings
from ..modules.ib_client_manager import IBClientManager

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
        self.manager = IBClientManager()
        self._check_connection()

    def _check_connection(self):
        """Check IB connection status."""
        try:
            client = asyncio.run(self.manager.get_client())
            if client:
                asyncio.run(client._ensure_connected())
                self.connected = client.ib.isConnected()
            else:
                self.connected = False
        except Exception as e:
            logger.warning(f"IB connection failed: {e}")
            self.connected = False

    async def _fetch_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Internal async helper to fetch option chain and spot price."""
        client = await self.manager.get_client()
        await client._ensure_connected()

        atm_options = await client.get_atm_options([symbol], days_to_expiry=0)
        if not atm_options:
            raise ValueError("No option data returned")

        current_price = atm_options[0].get("underlying_price_at_fetch", 0.0)

        strikes_data = {}
        for opt in atm_options:
            strike = float(opt.get("strike", 0))
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
                    "dte": 0,
                }

            if opt.get("right") == "C":
                strikes_data[strike]["call_oi"] = opt.get("open_interest", 0) or 0
                strikes_data[strike]["call_iv"] = (
                    opt.get("implied_volatility", 0.20) or 0.20
                )
                strikes_data[strike]["call_bid"] = opt.get("bid", 0.0) or 0.0
                strikes_data[strike]["call_ask"] = opt.get("ask", 0.0) or 0.0
                strikes_data[strike]["call_gamma"] = opt.get("gamma", 0.0) or 0.0
                strikes_data[strike]["call_delta"] = (
                    opt.get("delta", 0.0)
                    if opt.get("delta") is not None
                    else (0.5 if strike >= current_price else 0.3)
                )
            else:
                strikes_data[strike]["put_oi"] = opt.get("open_interest", 0) or 0
                strikes_data[strike]["put_iv"] = (
                    opt.get("implied_volatility", 0.20) or 0.20
                )
                strikes_data[strike]["put_bid"] = opt.get("bid", 0.0) or 0.0
                strikes_data[strike]["put_ask"] = opt.get("ask", 0.0) or 0.0
                strikes_data[strike]["put_gamma"] = opt.get("gamma", 0.0) or 0.0
                strikes_data[strike]["put_delta"] = (
                    opt.get("delta", 0.0)
                    if opt.get("delta") is not None
                    else (-0.5 if strike <= current_price else -0.3)
                )

        option_chain = list(strikes_data.values())
        option_chain.sort(key=lambda x: x["strike"])

        return {
            "symbol": symbol,
            "current_price": current_price,
            "option_chain": option_chain,
        }

    async def _fetch_spot_price(self, symbol: str) -> float:
        """Internal async helper to fetch only spot price."""
        client = await self.manager.get_client()
        await client._ensure_connected()
        underlying = await client.qualify_underlying_with_fallback(symbol)
        if not underlying:
            raise ValueError("Unable to qualify underlying")
        tickers = await client.ib.reqTickersAsync(underlying)
        if tickers and tickers[0] and (tickers[0].marketPrice() or tickers[0].close):
            price = (
                tickers[0].marketPrice()
                if tickers[0].marketPrice()
                else tickers[0].close
            )
            return price
        raise ValueError("No market price available")

    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from IB."""
        if not self.is_connected():
            if settings.ibkr_fallback_to_yahoo:
                logger.info("IB not connected, falling back to Yahoo")
                return YahooDataProvider().get_option_chain(symbol)
            raise ConnectionError("IB not connected")

        try:
            return asyncio.run(self._fetch_option_chain(symbol))
        except Exception as e:
            logger.warning(f"IB option chain fetch failed: {e}")
            if settings.ibkr_fallback_to_yahoo:
                logger.info("Falling back to Yahoo for option chain")
                return YahooDataProvider().get_option_chain(symbol)
            raise

    def get_spot_price(self, symbol: str) -> float:
        """Get spot price from IB."""
        if not self.is_connected():
            if settings.ibkr_fallback_to_yahoo:
                logger.info("IB not connected, falling back to Yahoo")
                return YahooDataProvider().get_spot_price(symbol)
            raise ConnectionError("IB not connected")

        try:
            return asyncio.run(self._fetch_spot_price(symbol))
        except Exception as e:
            logger.warning(f"IB spot price fetch failed: {e}")
            if settings.ibkr_fallback_to_yahoo:
                logger.info("Falling back to Yahoo for spot price")
                return YahooDataProvider().get_spot_price(symbol)
            raise

    def is_connected(self) -> bool:
        """Check connection status by verifying IB client."""
        try:
            client = asyncio.run(self.manager.get_client())
            return client is not None and client.ib.isConnected()
        except Exception:
            return False


class YahooDataProvider:
    """Yahoo Finance data provider."""

    def __init__(self):
        self.connected = True  # Yahoo is always "connected"

    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from Yahoo Finance."""
        # Would use yfinance here
        return {"symbol": symbol, "option_chain": []}

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
            with open(self.cache_path, "r") as f:
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


__all__ = [
    "DataProvider",
    "get_provider",
    "IBDataProvider",
    "YahooDataProvider",
    "FileDataProvider",
]
