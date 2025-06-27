"""
Data providers module for Magic8-Companion.
Provides a unified interface for different data sources (IB, Yahoo, Polygon).
"""

from typing import Protocol, Dict, Any, Optional
import logging
import asyncio
import pandas as pd
from pathlib import Path
from ..unified_config import settings
from ..modules.ib_client_manager import IBClientManager

logger = logging.getLogger(__name__)


class DataProvider(Protocol):
    """Protocol for asynchronous data providers."""

    async def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain data for a symbol."""
        ...

    async def get_spot_price(self, symbol: str) -> float:
        """Get current spot price for a symbol."""
        ...

    async def is_connected(self) -> bool:
        """Check if provider is connected and ready."""
        ...

    async def get_historical_data(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Get historical OHLCV data."""
        ...


class IBDataProvider:
    """Interactive Brokers data provider."""

    def __init__(self):
        self.connected = False
        self.manager = IBClientManager()

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

    async def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from IB."""
        if not await self.is_connected():
            if settings.ibkr_fallback_to_yahoo:
                logger.info("IB not connected, falling back to Yahoo")
                return await YahooDataProvider().get_option_chain(symbol)
            raise ConnectionError("IB not connected")

        try:
            return await self._fetch_option_chain(symbol)
        except Exception as e:
            logger.warning(f"IB option chain fetch failed: {e}")
            if settings.ibkr_fallback_to_yahoo:
                logger.info("Falling back to Yahoo for option chain")
                return await YahooDataProvider().get_option_chain(symbol)
            raise

    async def get_spot_price(self, symbol: str) -> float:
        """Get spot price from IB."""
        if not await self.is_connected():
            if settings.ibkr_fallback_to_yahoo:
                logger.info("IB not connected, falling back to Yahoo")
                return await YahooDataProvider().get_spot_price(symbol)
            raise ConnectionError("IB not connected")

        try:
            return await self._fetch_spot_price(symbol)
        except Exception as e:
            logger.warning(f"IB spot price fetch failed: {e}")
            if settings.ibkr_fallback_to_yahoo:
                logger.info("Falling back to Yahoo for spot price")
                return await YahooDataProvider().get_spot_price(symbol)
            raise

    async def is_connected(self) -> bool:
        """Check connection status by verifying IB client."""
        try:
            client = await self.manager.get_client()
            if client:
                await client._ensure_connected()
                return client.ib.isConnected()
            return False
        except Exception:
            return False

    async def get_historical_data(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Fetch historical bars from IBKR or fallback provider."""
        if not await self.is_connected():
            if settings.ibkr_fallback_to_yahoo:
                logger.info("IB not connected, falling back to Yahoo for bars")
                return await YahooDataProvider().get_historical_data(symbol, interval, period)
            raise ConnectionError("IB not connected")

        try:
            client = await self.manager.get_client()
            await client._ensure_connected()
            underlying = await client.qualify_underlying_with_fallback(symbol)
            if not underlying:
                raise ValueError("Unable to qualify underlying")

            # Map interval/period to IB format
            bar_size = interval.replace('m', ' mins').replace('d', ' day').replace('h', ' hour')
            duration = period.replace('d', ' D').replace('w', ' W').replace('m', ' M').replace('y', ' Y')

            bars = await client.ib.reqHistoricalDataAsync(
                underlying,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=False,
                formatDate=1,
                keepUpToDate=False,
                chartOptions=[],
                timeout=15,
            )

            records = [
                {
                    "datetime": b.date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ]
            df = pd.DataFrame.from_records(records)
            if not df.empty:
                df["datetime"] = pd.to_datetime(df["datetime"])
                df.set_index("datetime", inplace=True)
            return df
        except Exception as e:
            logger.warning(f"IB historical data fetch failed: {e}")
            if settings.ibkr_fallback_to_yahoo:
                logger.info("Falling back to Yahoo for bars")
                return await YahooDataProvider().get_historical_data(symbol, interval, period)
            raise


class YahooDataProvider:
    """Yahoo Finance data provider."""

    def __init__(self):
        self.connected = True  # Yahoo is always "connected"

    async def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from Yahoo Finance."""
        import yfinance as yf
        ticker = yf.Ticker(self._map_symbol(symbol))
        chain = await asyncio.to_thread(lambda: ticker.option_chain())
        if not chain or chain.calls.empty:
            return {"symbol": symbol, "option_chain": []}
        calls = chain.calls
        puts = chain.puts
        option_chain = []
        for _, row in calls.iterrows():
            option_chain.append({
                "strike": float(row["strike"]),
                "call_oi": int(row.get("openInterest", 0) or 0),
                "call_iv": float(row.get("impliedVolatility", 0) or 0),
                "call_bid": float(row.get("bid", 0) or 0),
                "call_ask": float(row.get("ask", 0) or 0),
                "call_volume": int(row.get("volume", 0) or 0),
            })
        for _, row in puts.iterrows():
            strike = float(row["strike"])
            match = next((o for o in option_chain if o["strike"] == strike), None)
            if match:
                match.update({
                    "put_oi": int(row.get("openInterest", 0) or 0),
                    "put_iv": float(row.get("impliedVolatility", 0) or 0),
                    "put_bid": float(row.get("bid", 0) or 0),
                    "put_ask": float(row.get("ask", 0) or 0),
                    "put_volume": int(row.get("volume", 0) or 0),
                })
            else:
                option_chain.append({
                    "strike": strike,
                    "put_oi": int(row.get("openInterest", 0) or 0),
                    "put_iv": float(row.get("impliedVolatility", 0) or 0),
                    "put_bid": float(row.get("bid", 0) or 0),
                    "put_ask": float(row.get("ask", 0) or 0),
                    "put_volume": int(row.get("volume", 0) or 0),
                })
        option_chain.sort(key=lambda x: x["strike"])
        price = await self.get_spot_price(symbol)
        return {"symbol": symbol, "current_price": price, "option_chain": option_chain}

    async def get_spot_price(self, symbol: str) -> float:
        """Get spot price from Yahoo."""
        import yfinance as yf
        ticker = yf.Ticker(self._map_symbol(symbol))
        data = await asyncio.to_thread(lambda: ticker.history(period="1d", interval="1m"))
        if isinstance(data, pd.DataFrame) and not data.empty:
            return float(data["Close"].iloc[-1])
        return 0.0

    async def is_connected(self) -> bool:
        """Yahoo is always available."""
        return True

    def _map_symbol(self, symbol: str) -> str:
        mapping = {"SPX": "^GSPC", "VIX": "^VIX"}
        return mapping.get(symbol, symbol)

    async def get_historical_data(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance."""
        import yfinance as yf
        ticker = yf.Ticker(self._map_symbol(symbol))
        data = await asyncio.to_thread(ticker.history, interval=interval, period=period)
        if isinstance(data, pd.DataFrame):
            return data
        return pd.DataFrame()


class FileDataProvider:
    """File-based data provider for cached data."""

    def __init__(self, cache_path: str = "data/market_data_cache.json"):
        self.cache_path = cache_path
        self.connected = True

    async def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from cached file."""
        import json
        import os

        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                data = json.load(f)
                return data.get(symbol, {"symbol": symbol, "option_chain": []})

        return {"symbol": symbol, "option_chain": []}

    async def get_spot_price(self, symbol: str) -> float:
        """Get spot price from cache."""
        data = await self.get_option_chain(symbol)
        return data.get("current_price", 0.0)

    async def get_historical_data(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Load historical data from cached CSV/JSON if available."""
        base = Path(self.cache_path).parent
        csv_file = base / f"{symbol}_{interval}_{period}.csv"
        json_file = base / f"{symbol}_{interval}_{period}.json"
        if csv_file.exists():
            return pd.read_csv(csv_file)
        if json_file.exists():
            import json
            with open(json_file) as f:
                data = json.load(f)
            return pd.DataFrame(data)
        return pd.DataFrame()

    async def is_connected(self) -> bool:
        """File provider is always ready."""
        return True


# Singleton instances of data providers
_ib_provider_instance: Optional[IBDataProvider] = None
_yahoo_provider_instance: Optional[YahooDataProvider] = None
_file_provider_instance: Optional[FileDataProvider] = None


def get_provider(provider_name: Optional[str] = None) -> DataProvider:
    """
    Get a singleton data provider instance.

    Args:
        provider_name: Name of provider (ib, yahoo, file).
                      If None, uses settings.data_provider

    Returns:
        DataProvider instance (singleton)
    """
    global _ib_provider_instance, _yahoo_provider_instance, _file_provider_instance
    
    if provider_name is None:
        provider_name = settings.data_provider

    provider_name = provider_name.lower()

    if provider_name == "ib":
        if _ib_provider_instance is None:
            _ib_provider_instance = IBDataProvider()
        return _ib_provider_instance

    elif provider_name == "yahoo":
        if _yahoo_provider_instance is None:
            _yahoo_provider_instance = YahooDataProvider()
        return _yahoo_provider_instance

    elif provider_name == "file":
        if _file_provider_instance is None:
            _file_provider_instance = FileDataProvider()
        return _file_provider_instance

    else:
        logger.warning(f"Unknown provider {provider_name}, defaulting to file")
        if _file_provider_instance is None:
            _file_provider_instance = FileDataProvider()
        return _file_provider_instance


__all__ = [
    "DataProvider",
    "get_provider",
    "IBDataProvider",
    "YahooDataProvider",
    "FileDataProvider",
]
