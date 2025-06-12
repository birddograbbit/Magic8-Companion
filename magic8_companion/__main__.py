"""
Entry point for running Magic8-Companion as a module.
Usage: python -m magic8_companion
"""

import asyncio

from .main import main

if __name__ == "__main__":
    asyncio.run(main())
