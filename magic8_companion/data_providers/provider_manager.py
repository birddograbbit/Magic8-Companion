"""
Singleton Data Provider Manager for Magic8-Companion.
Ensures only one instance of each data provider type is created,
preventing multiple IB connections with the same client ID.
"""
import asyncio
from typing import Dict, Optional
import logging
from .import DataProvider, get_provider

logger = logging.getLogger(__name__)


class DataProviderManager:
    """Singleton manager for data provider instances."""
    
    _instance: Optional['DataProviderManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataProviderManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._providers: Dict[str, DataProvider] = {}
        logger.info("DataProviderManager singleton initialized")
        
    async def get_provider(self, provider_name: Optional[str] = None) -> DataProvider:
        """Get or create a data provider instance.
        
        Args:
            provider_name: Name of provider (ib, yahoo, file).
                         If None, uses settings.data_provider
                         
        Returns:
            DataProvider instance (cached/singleton)
        """
        from ..unified_config import settings
        
        if provider_name is None:
            provider_name = settings.data_provider
            
        provider_name = provider_name.lower()
        
        async with self._lock:
            # Return existing provider if available
            if provider_name in self._providers:
                logger.debug(f"Returning cached {provider_name} provider")
                return self._providers[provider_name]
            
            # Create new provider
            logger.info(f"Creating new {provider_name} provider instance")
            provider = get_provider(provider_name)
            self._providers[provider_name] = provider
            
            # For IB provider, ensure connection
            if provider_name == "ib":
                try:
                    if await provider.is_connected():
                        logger.info("IB provider connected successfully")
                    else:
                        logger.warning("IB provider created but not connected")
                except Exception as e:
                    logger.error(f"Error checking IB connection: {e}")
            
            return provider
    
    async def disconnect_all(self):
        """Disconnect all providers (mainly for IB)."""
        async with self._lock:
            for name, provider in self._providers.items():
                if hasattr(provider, 'manager') and hasattr(provider.manager, 'disconnect'):
                    try:
                        logger.info(f"Disconnecting {name} provider")
                        await provider.manager.disconnect()
                    except Exception as e:
                        logger.error(f"Error disconnecting {name} provider: {e}")
            
            # Clear the cache
            self._providers.clear()
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None


# Global instance getter
_manager = DataProviderManager()

async def get_shared_provider(provider_name: Optional[str] = None) -> DataProvider:
    """Get a shared data provider instance from the singleton manager.
    
    This is the main entry point that should be used throughout the application
    to ensure all components share the same data provider instances.
    """
    return await _manager.get_provider(provider_name)

async def disconnect_all_providers():
    """Disconnect all data providers."""
    await _manager.disconnect_all()
