#!/usr/bin/env python3
"""
Legacy main_simplified.py - DEPRECATED
This file now proxies to unified_main.py in simple mode for backward compatibility.

MIGRATION PATH:
- Set M8C_SYSTEM_COMPLEXITY=simple in .env and use unified_main.py
- Or run the application using: python -m magic8_companion
"""
import warnings
import os

# Issue deprecation warning
warnings.warn(
    "main_simplified.py is deprecated. Set M8C_SYSTEM_COMPLEXITY=simple and use unified_main.py. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Force simple mode for this legacy entry point
os.environ['M8C_SYSTEM_COMPLEXITY'] = 'simple'

# Import everything from unified_main for backward compatibility
from .unified_main import *

# If this file is run directly, use the unified main in simple mode
if __name__ == '__main__':
    import asyncio
    from .unified_main import main
    asyncio.run(main())
