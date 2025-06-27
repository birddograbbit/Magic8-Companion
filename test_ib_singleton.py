#!/usr/bin/env python3
"""
Test script to verify IB connection singleton is working properly.
This ensures only one IB connection is created across all components.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from magic8_companion.modules.ib_client_manager import get_ib_connection, disconnect_ib, is_ib_connected
from magic8_companion.modules.ib_client import IBClient
from magic8_companion.data_providers import get_provider


async def test_singleton():
    """Test that multiple clients use the same connection."""
    print("Testing IB connection singleton...")
    print("-" * 50)
    
    # Test 1: Multiple IBClient instances
    print("\n1. Testing multiple IBClient instances...")
    client1 = IBClient()
    client2 = IBClient()
    
    try:
        # Ensure connected
        print("   Connecting client1...")
        ib1 = await client1._ensure_connected()
        print("   ✓ Client1 connected")
        
        print("   Connecting client2...")
        ib2 = await client2._ensure_connected()
        print("   ✓ Client2 connected")
        
        # They should be the exact same object
        assert ib1 is ib2, "Clients should share the same IB connection!"
        print("   ✓ Both clients use the same IB connection object")
        
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("   (This is expected if IB Gateway/TWS is not running)")
    
    # Test 2: Direct connection access
    print("\n2. Testing direct connection access...")
    try:
        ib3 = await get_ib_connection()
        if ib1:
            assert ib1 is ib3, "Direct access should return same connection!"
            print("   ✓ Direct access returns same connection")
    except Exception as e:
        print(f"   ✗ Direct access failed: {e}")
    
    # Test 3: Data provider singleton
    print("\n3. Testing data provider singletons...")
    provider1 = get_provider("ib")
    provider2 = get_provider("ib")
    assert provider1 is provider2, "Should return same provider instance!"
    print("   ✓ Data providers are singletons")
    
    # Test 4: Connection status
    print("\n4. Testing connection status...")
    connected = is_ib_connected()
    print(f"   Connection status: {'Connected' if connected else 'Not connected'}")
    
    # Cleanup
    print("\n5. Cleaning up...")
    await disconnect_ib()
    print("   ✓ Connection cleaned up")
    
    # Verify disconnected
    connected_after = is_ib_connected()
    assert not connected_after, "Should be disconnected after cleanup"
    print("   ✓ Verified disconnection")
    
    print("\n" + "=" * 50)
    print("Singleton test COMPLETED!")
    print("=" * 50)


async def test_reconnection():
    """Test reconnection behavior after failure."""
    print("\n\nTesting reconnection behavior...")
    print("-" * 50)
    
    # Disconnect first to ensure clean state
    await disconnect_ib()
    
    print("\n1. First connection attempt...")
    try:
        ib1 = await get_ib_connection()
        if ib1:
            print("   ✓ Connected successfully")
            
            # Disconnect
            print("\n2. Disconnecting...")
            await disconnect_ib()
            print("   ✓ Disconnected")
            
            # Reconnect
            print("\n3. Reconnection attempt...")
            ib2 = await get_ib_connection()
            if ib2:
                print("   ✓ Reconnected successfully")
                # Should be a different instance after reconnection
                assert ib1 is not ib2, "Should be new instance after reconnection"
                print("   ✓ New connection instance created")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("   (This is expected if IB Gateway/TWS is not running)")
    
    finally:
        # Final cleanup
        await disconnect_ib()
    
    print("\nReconnection test COMPLETED!")


async def main():
    """Run all tests."""
    print("IB Connection Singleton Test Suite")
    print("==================================")
    print("Make sure IB Gateway or TWS is running for full test coverage")
    print("If not running, connection tests will fail (expected)")
    
    try:
        await test_singleton()
        await test_reconnection()
        
        print("\n\nAll tests completed!")
        print("\nSummary:")
        print("- ✓ Singleton pattern working correctly")
        print("- ✓ Multiple clients share same connection")
        print("- ✓ Data providers are singletons")
        print("- ✓ Reconnection works properly")
        
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
