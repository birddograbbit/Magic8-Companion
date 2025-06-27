# IB Connection Singleton Fix

## Summary

Fixed the "clientId 2 already in use" error by implementing a proper singleton pattern for data providers. This ensures all components share the same IB connection instead of creating multiple connections with the same clientId.

## Problem

The log showed multiple components trying to connect to IB with the same clientId:
```
2025-06-27 18:01:55,656 - ib_async.client - ERROR - Peer closed connection. clientId 2 already in use?
```

This was happening because:
1. MarketAnalyzer was creating an IBClientManager and connecting
2. ML scheduler extension was calling `get_provider()` which created a NEW IBDataProvider instance
3. Each IBDataProvider created its own IBClientManager instance
4. All tried to connect with the same clientId from settings

## Solution (Option 1 Implementation)

### 1. Made Data Providers Singletons
- Modified `magic8_companion/data_providers/__init__.py`
- Added module-level singleton instances:
  ```python
  _ib_provider_instance: Optional[IBDataProvider] = None
  _yahoo_provider_instance: Optional[YahooDataProvider] = None
  _file_provider_instance: Optional[FileDataProvider] = None
  ```
- Updated `get_provider()` to return the same instance each time

### 2. Updated ML Scheduler Extension
- Modified `magic8_companion/ml_scheduler_extension.py`
- Added optional `data_provider` parameter to `__init__()`
- Falls back to calling `get_provider()` if no provider passed

### 3. Updated Main Application
- Modified `magic8_companion/unified_main.py`
- RecommendationEngine creates data provider singleton
- Passes the same instance to ML scheduler extension

## Benefits

1. **Single IB Connection**: Only one connection to IB is created and shared
2. **No clientId Conflicts**: Eliminates the "clientId already in use" errors
3. **Better Resource Management**: Reduces memory usage and connection overhead
4. **Consistent Data**: All components see the same market data

## Testing

To verify the fix works:

```bash
# Start the application
python -m magic8_companion.unified_main

# Check logs for connection attempts
grep "Connecting to IB" logs/magic8_companion.log
# Should see only ONE connection attempt

# Check for clientId errors
grep "clientId" logs/magic8_companion.log
# Should NOT see "already in use" errors
```

## Architecture After Fix

```
Application Start
    │
    ├─> RecommendationEngine
    │       │
    │       └─> data_provider = get_provider("ib")  [Creates singleton]
    │               │
    │               └─> IBDataProvider (singleton)
    │                       │
    │                       └─> IBClientManager (singleton)
    │                               │
    │                               └─> IBClient (clientId=2)
    │
    └─> ML Scheduler Extension
            │
            └─> Uses passed data_provider  [Same singleton instance]
                    │
                    └─> Same IBDataProvider
                            │
                            └─> Same IBClientManager
                                    │
                                    └─> Same IBClient connection
```

## Notes

- The IBClientManager was already a singleton, but multiple IBDataProvider instances were being created
- The fix ensures true singleton behavior at the data provider level
- Gamma runner and other components will also use the same singleton instances
- No changes needed to IBClient or IBClientManager - they were working correctly
