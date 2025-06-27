"""
Singleton IB Client Manager to ensure only one IB connection is created.
This prevents client ID conflicts when multiple MarketAnalyzer instances are created.
"""
import asyncio
from typing import Optional
from ib_async import IB
from ..unified_config import settings
import logging

logger = logging.getLogger(__name__)


class IBConnectionSingleton:
    """True singleton for IB connection management."""
    
    _instance: Optional['IBConnectionSingleton'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IBConnectionSingleton, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._ib: Optional[IB] = None
        self._connecting = False
        self._last_connection_attempt = None
        
    async def get_connection(self) -> Optional[IB]:
        """Get or create the singleton IB connection."""
        async with self._lock:
            # If we're already connecting, wait
            if self._connecting:
                logger.info("Another connection attempt in progress, waiting...")
                await asyncio.sleep(1)
                return self._ib if self._ib and self._ib.isConnected() else None
                
            # If we have a connected IB instance, return it
            if self._ib and self._ib.isConnected():
                return self._ib
                
            # If we have a disconnected IB instance, clean it up
            if self._ib:
                logger.info("Cleaning up disconnected IB instance")
                try:
                    self._ib.disconnect()
                except:
                    pass
                self._ib = None
            
            # Create new connection
            self._connecting = True
            try:
                logger.info(f"Creating new IB connection to {settings.ib_host}:{settings.ib_port} with clientId {settings.ib_client_id}")
                self._ib = IB()
                
                await self._ib.connectAsync(
                    host=settings.ib_host,
                    port=settings.ib_port,
                    clientId=settings.ib_client_id,
                    timeout=10
                )
                
                if self._ib.isConnected():
                    logger.info("Successfully connected to IB")
                    return self._ib
                else:
                    logger.error("IB connection failed - not connected after connect attempt")
                    self._ib = None
                    return None
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout connecting to IB on {settings.ib_host}:{settings.ib_port}")
                if self._ib:
                    try:
                        self._ib.disconnect()
                    except:
                        pass
                self._ib = None
                return None
                
            except Exception as e:
                logger.error(f"Error connecting to IB: {e}")
                if self._ib:
                    try:
                        self._ib.disconnect()
                    except:
                        pass
                self._ib = None
                return None
                
            finally:
                self._connecting = False
    
    async def disconnect(self):
        """Disconnect the IB connection."""
        async with self._lock:
            if self._ib:
                logger.info("Disconnecting IB connection")
                try:
                    self._ib.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")
                finally:
                    self._ib = None
    
    def is_connected(self) -> bool:
        """Check if IB is connected."""
        return self._ib is not None and self._ib.isConnected()


# Global singleton instance
_ib_connection = IBConnectionSingleton()


async def get_ib_connection() -> Optional[IB]:
    """Get the singleton IB connection."""
    return await _ib_connection.get_connection()


async def disconnect_ib():
    """Disconnect the singleton IB connection."""
    await _ib_connection.disconnect()


def is_ib_connected() -> bool:
    """Check if IB is connected."""
    return _ib_connection.is_connected()


# Legacy IBClientManager for backward compatibility
class IBClientManager:
    """Legacy manager - now just wraps the singleton connection."""
    
    def __init__(self):
        pass
    
    async def get_client(self):
        """Returns a wrapper that uses the singleton connection."""
        # Import here to avoid circular imports
        from .ib_client import IBClient
        
        # Create a client wrapper that uses the singleton connection
        client = IBClientWrapper()
        return client
    
    async def disconnect(self):
        """Disconnect the IB connection."""
        await disconnect_ib()
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        global _ib_connection
        if _ib_connection:
            asyncio.create_task(disconnect_ib())
        _ib_connection = IBConnectionSingleton()


class IBClientWrapper:
    """Wrapper that provides IBClient interface using singleton connection."""
    
    def __init__(self):
        self.oi_fetcher = None
        
    @property
    def ib(self):
        """Get the IB connection (for compatibility)."""
        # This is synchronous but returns the last known connection
        # The actual connection is managed by the singleton
        return _ib_connection._ib
    
    async def _ensure_connected(self):
        """Ensure IB is connected."""
        conn = await get_ib_connection()
        if not conn:
            raise ConnectionError("Failed to connect to IB or not currently connected.")
        
        # Initialize OI fetcher after successful connection if needed
        if settings.enable_oi_streaming and not self.oi_fetcher:
            from .ib_oi_fetcher import IBOpenInterestFetcher
            self.oi_fetcher = IBOpenInterestFetcher(conn)
            logger.info("OI streaming enabled")
    
    async def disconnect(self):
        """Disconnect (delegates to singleton)."""
        await disconnect_ib()
        self.oi_fetcher = None
    
    # All the other IBClient methods should be here, but they would need to be refactored
    # to use the singleton connection. For now, we'll import the original IBClient methods
    async def get_positions(self):
        from .ib_client import IBClient
        await self._ensure_connected()
        # Create temporary client using regular construction
        temp_client = IBClient()
        temp_client.oi_fetcher = self.oi_fetcher
        return await temp_client.get_positions()
    
    async def qualify_underlying_with_fallback(self, symbol_name: str):
        from .ib_client import IBClient
        await self._ensure_connected()
        temp_client = IBClient()
        return await temp_client.qualify_underlying_with_fallback(symbol_name)
    
    async def qualify_option_with_fallback(self, symbol_name: str, expiry_date: str, strike: float, right: str, trading_class: str = None):
        from .ib_client import IBClient
        await self._ensure_connected()
        temp_client = IBClient()
        return await temp_client.qualify_option_with_fallback(symbol_name, expiry_date, strike, right, trading_class)
    
    async def get_atm_options(self, symbols, days_to_expiry=0):
        from .ib_client import IBClient
        await self._ensure_connected()
        temp_client = IBClient()
        temp_client.oi_fetcher = self.oi_fetcher
        return await temp_client.get_atm_options(symbols, days_to_expiry)
