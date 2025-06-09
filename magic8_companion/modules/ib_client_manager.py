"""
Singleton IB Client Manager to ensure only one IB connection is created.
This prevents client ID conflicts when multiple MarketAnalyzer instances are created.
"""
import asyncio
from typing import Optional
from .ib_client import IBClient
from ..config import settings


class IBClientManager:
    """Singleton manager for IB client connections."""
    
    _instance: Optional['IBClientManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IBClientManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._client: Optional[IBClient] = None
        
    async def get_client(self) -> Optional[IBClient]:
        """Get or create the singleton IB client instance."""
        async with self._lock:
            if self._client is None:
                try:
                    self._client = IBClient(
                        host=settings.ib_host,
                        port=settings.ib_port,
                        client_id=settings.ib_client_id
                    )
                except Exception as e:
                    print(f"Failed to create IB client: {e}")
                    return None
            
            return self._client
    
    async def disconnect(self):
        """Disconnect the IB client if connected."""
        async with self._lock:
            if self._client:
                await self._client.disconnect()
                self._client = None
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance and cls._instance._client:
            # Note: This is synchronous, may need to be called from async context
            # In production, use disconnect() instead
            cls._instance._client = None
        cls._instance = None
