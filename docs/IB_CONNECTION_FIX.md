# IB Connection Singleton Fix - Updated Implementation

## Summary

Fixed the "clientId 2 already in use" error by implementing a true singleton pattern for the IB connection itself. This ensures only ONE IB() instance is created and shared across all components.

## Problem

The log showed multiple components trying to connect to IB with the same clientId:
```
2025-06-27 18:01:55,656 - ib_async.client - ERROR - Peer closed connection. clientId 2 already in use?
```

The initial fix (making data providers singletons) wasn't sufficient because:
1. Each IBClient was still creating its own IB() instance
2. Connection failures weren't properly cleaning up
3. Multiple connection attempts were happening simultaneously

## Solution - True IB Connection Singleton

### 1. Created IBConnectionSingleton
- New class in `ib_client_manager.py` that manages a single IB() instance
- Handles connection creation, cleanup, and reconnection
- Prevents simultaneous connection attempts with a lock
- Properly cleans up failed connections

### 2. Updated IBClient
- No longer creates its own IB() instance
- Uses `get_ib_connection()` to get the singleton connection
- All IBClient instances share the same underlying IB connection

### 3. Architecture After Fix

```
Application
    │
    ├─> IBConnectionSingleton (Global)
    │       │
    │       └─> IB() instance (Only ONE ever created)
    │
    ├─> RecommendationEngine
    │       │
    │       └─> IBDataProvider (singleton)
    │               │
    │               └─> IBClientManager
    │                       │
    │                       └─> IBClient → uses get_ib_connection()
    │
    └─> ML Scheduler Extension
            │
            └─> Same IBDataProvider (singleton)
                    │
                    └─> Same IBClientManager
                            │
                            └─> Same IBClient → uses get_ib_connection()

All components ultimately use the SAME IB() instance
```

## Key Changes

### ib_client_manager.py
```python
class IBConnectionSingleton:
    """True singleton for IB connection management."""
    
    async def get_connection(self) -> Optional[IB]:
        """Get or create the singleton IB connection."""
        # Only creates ONE IB() instance
        # Handles cleanup of failed connections
        # Prevents simultaneous connection attempts
```

### ib_client.py
```python
class IBClient:
    def __init__(self, ...):
        # Don't create our own IB instance - use the singleton
        
    async def _ensure_connected(self):
        """Ensure we have a connection from the singleton."""
        ib = await get_ib_connection()
        if not ib:
            raise ConnectionError("Failed to connect to IB")
        return ib
```

## Benefits

1. **True Single Connection**: Only one IB() instance ever exists
2. **No clientId Conflicts**: Impossible to have duplicate connections
3. **Proper Cleanup**: Failed connections are properly cleaned up
4. **Thread-Safe**: Connection creation is protected by asyncio locks
5. **Automatic Retry**: If connection drops, next request will reconnect

## Testing

To verify the fix:

```bash
# Start the application
python -m magic8_companion.unified_main

# Check logs - should see only ONE connection message
grep "Creating new IB connection" logs/magic8_companion.log

# Should NOT see any "clientId already in use" errors
grep "already in use" logs/magic8_companion.log

# Monitor connection status
tail -f logs/magic8_companion.log | grep -E "(Creating new IB|Successfully connected|Disconnecting)"
```

## Test Script

Create `test_ib_singleton.py`:

```python
import asyncio
from magic8_companion.modules.ib_client_manager import get_ib_connection, disconnect_ib
from magic8_companion.modules.ib_client import IBClient

async def test_singleton():
    """Test that multiple clients use the same connection."""
    print("Testing IB connection singleton...")
    
    # Create multiple clients
    client1 = IBClient()
    client2 = IBClient()
    
    # Ensure connected
    ib1 = await client1._ensure_connected()
    ib2 = await client2._ensure_connected()
    
    # They should be the exact same object
    assert ib1 is ib2, "Clients should share the same IB connection!"
    print("✓ Both clients use the same IB connection")
    
    # Test direct connection access
    ib3 = await get_ib_connection()
    assert ib1 is ib3, "Direct access should return same connection!"
    print("✓ Direct access returns same connection")
    
    # Cleanup
    await disconnect_ib()
    print("✓ Connection cleaned up")
    
    print("\nSingleton test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_singleton())
```

## Notes

- The IB() instance is created only when first needed
- If connection fails, the instance is properly cleaned up
- Next connection attempt will create a new instance
- All components automatically share the connection
- No changes needed to data providers or other components

## VIX Data Retrieval Issues

Occasionally the ML scheduler fails to fetch VIX bars from IBKR, resulting in
errors like `Unknown contract: Stock(symbol='VIX')`. The scheduler now retries
using Yahoo Finance when IBKR data is unavailable. If both sources fail, the
prediction step is skipped until data becomes available. Check the logs for
`VIX data fetch failed` messages when troubleshooting.
