#!/usr/bin/env python3
"""
Legacy main.py - DEPRECATED
This file now proxies to unified_main.py for backward compatibility.

MIGRATION PATH:
- Update external integrations to import from unified_main.py
- Or run the application using: python -m magic8_companion
"""
import warnings

# Issue deprecation warning
warnings.warn(
    "main.py is deprecated. Please use unified_main.py or run with 'python -m magic8_companion'. "
    "This file will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Import everything from unified_main for backward compatibility
from .unified_main import *

# If this file is run directly, use the unified main
if __name__ == '__main__':
    import asyncio
    from .unified_main import main
    asyncio.run(main())
