"""
Legacy config_simplified.py - DEPRECATED
This file now proxies to unified_config.py for backward compatibility.

MIGRATION PATH:
- Change imports from: from .config_simplified import settings
- Change imports to:   from .unified_config import settings
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "config_simplified.py is deprecated. Please use unified_config.py instead. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Proxy to the unified config with simple mode
from .unified_config import Settings, get_simplified_settings

# For backward compatibility, provide settings in simple mode
settings = get_simplified_settings()

# Maintain backward compatibility
__all__ = ['Settings', 'settings']
