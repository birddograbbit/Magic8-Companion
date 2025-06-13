"""
Legacy config.py - DEPRECATED
This file now proxies to unified_config.py for backward compatibility.

MIGRATION PATH:
- Change imports from: from .config import settings
- Change imports to:   from .unified_config import settings
"""
import warnings

# Issue deprecation warning  
warnings.warn(
    "config.py is deprecated. Please use unified_config.py instead. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to the unified config
from .unified_config import Settings, settings

# Maintain backward compatibility for all imports
__all__ = ['Settings', 'settings']
