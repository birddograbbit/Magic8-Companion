#!/usr/bin/env python3
"""
Quick test script to validate gamma functionality
Run this first to ensure basic setup is working
"""
import sys
import os
import json

print("Quick Gamma Migration Test")
print("=" * 60)

# Test 1: Import check
print("\n1. Testing imports...")
try:
    from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis
    from magic8_companion.unified_config import settings
    print("✅ Imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Configuration check
print("\n2. Checking configuration...")
try:
    print(f"   - System complexity: {settings.system_complexity}")
    print(f"   - Enhanced GEX enabled: {settings.enable_enhanced_gex}")
    print(f"   - Gamma symbols: {settings.gamma_symbols}")
    print(f"   - Data provider: {settings.data_provider}")
    print("✅ Configuration loaded")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

# Test 3: Run gamma analysis
print("\n3. Running gamma analysis for SPX...")
try:
    results = run_gamma_analysis('SPX')
    if results:
        print(f"✅ Analysis successful!")
        print(f"   - Net GEX: ${results.get('net_gex', 0):,.0f}")
        print(f"   - Regime: {results.get('regime', 'N/A')}")
        print(f"   - Levels found: {len(results.get('gamma_levels', []))}")
        
        # Save results for inspection
        with open('logs/quick_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n   Full results saved to: logs/quick_test_results.json")
    else:
        print("❌ Analysis returned no results")
        sys.exit(1)
except Exception as e:
    print(f"❌ Analysis failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All quick tests passed! Ready for comprehensive testing.")
print("\nNext steps:")
print("1. Run the full test suite: python test_gamma_migration.py")
print("2. Test the scheduler: python gamma_scheduler.py --mode scheduled --run-once")
print("3. Review logs in the logs/ directory")
