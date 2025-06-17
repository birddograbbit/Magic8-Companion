"""Magic8-Companion package"""

import asyncio

# Ensure an event loop exists for libraries like eventkit
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

__version__ = "1.0.0"
