"""
Entry point for running Magic8-Companion as a module.
Usage: python -m magic8_companion

Uses unified application with configurable complexity modes.
"""

import asyncio

from .unified_main import main

if __name__ == "__main__":
    asyncio.run(main())
