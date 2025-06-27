#!/usr/bin/env python3
"""
Debug script for ML timezone issue
"""
import sys
import os
from datetime import datetime, timezone
import pytz

# Add paths
MAGIC8_PATH = os.environ.get('MAGIC8_PATH', '.')
ML_PATH = os.environ.get('ML_PATH', '../MLOptionTrading')
sys.path.insert(0, MAGIC8_PATH)
sys.path.insert(0, ML_PATH)

print("=== ML Timezone Debug Script ===")
print(f"Python version: {sys.version}")
print(f"Magic8 path: {MAGIC8_PATH}")
print(f"ML path: {ML_PATH}")
print()

# Test datetime creation methods
print("=== Testing datetime creation methods ===")

# Method 1: deprecated utcnow
try:
    dt1 = datetime.utcnow()
    print(f"datetime.utcnow(): {dt1}, tzinfo={dt1.tzinfo}")
except Exception as e:
    print(f"datetime.utcnow() failed: {e}")

# Method 2: new Python 3.12+ way
try:
    dt2 = datetime.now(timezone.utc).replace(tzinfo=None)
    print(f"datetime.now(timezone.utc).replace(tzinfo=None): {dt2}, tzinfo={dt2.tzinfo}")
except Exception as e:
    print(f"datetime.now(timezone.utc).replace(tzinfo=None) failed: {e}")

# Method 3: datetime.now() without timezone
try:
    dt3 = datetime.now()
    print(f"datetime.now(): {dt3}, tzinfo={dt3.tzinfo}")
except Exception as e:
    print(f"datetime.now() failed: {e}")

print()

# Test pytz localization
print("=== Testing pytz localization ===")
est = pytz.timezone('US/Eastern')
naive_dt = datetime(2025, 6, 27, 14, 30, 0)  # Naive datetime

print(f"Naive datetime: {naive_dt}, tzinfo={naive_dt.tzinfo}")

# Test localize on naive datetime
try:
    localized = est.localize(naive_dt)
    print(f"Localized datetime: {localized}, tzinfo={localized.tzinfo}")
except Exception as e:
    print(f"Localization failed: {e}")

# Test localize on aware datetime (should fail)
print("\nTesting localize on aware datetime (should fail):")
aware_dt = datetime.now(timezone.utc)
print(f"Aware datetime: {aware_dt}, tzinfo={aware_dt.tzinfo}")
try:
    bad_localized = est.localize(aware_dt)
    print(f"ERROR: This should have failed but didn't: {bad_localized}")
except ValueError as e:
    print(f"Expected error: {e}")

# Test utcoffset
print("\nTesting utcoffset:")
try:
    # This should work - calling utcoffset on a localized datetime
    offset1 = localized.utcoffset()
    print(f"utcoffset on localized datetime: {offset1}")
except Exception as e:
    print(f"utcoffset failed: {e}")

try:
    # This will fail - calling est.utcoffset on an aware datetime
    offset2 = est.utcoffset(aware_dt)
    print(f"est.utcoffset on aware datetime: {offset2}")
except Exception as e:
    print(f"Expected error - est.utcoffset on aware datetime: {e}")

print()

# Check if patch is loaded
print("=== Checking ML timezone patch ===")
try:
    from magic8_companion.patches.ml_timezone_patch import apply_patch
    print("✓ Patch module imported successfully")
    
    # Check if ML system is available
    try:
        from ml.enhanced_ml_system import FeatureEngineer
        print("✓ ML enhanced_ml_system imported successfully")
        
        # Check if patch is applied
        if hasattr(FeatureEngineer.create_temporal_features, '_patched'):
            print("✓ Patch is applied to create_temporal_features")
        else:
            print("✗ Patch is NOT applied to create_temporal_features")
            print("  Applying patch now...")
            apply_patch()
            if hasattr(FeatureEngineer.create_temporal_features, '_patched'):
                print("✓ Patch applied successfully")
            else:
                print("✗ Patch application failed")
    except ImportError as e:
        print(f"✗ Could not import ML enhanced_ml_system: {e}")
        
except ImportError as e:
    print(f"✗ Could not import patch module: {e}")

print()

# Test the actual problem
print("=== Reproducing the actual error ===")
try:
    from ml.enhanced_ml_system import FeatureEngineer
    
    # Create a FeatureEngineer instance (mock the required attributes)
    class MockFeatureEngineer(FeatureEngineer):
        def __init__(self):
            self.est = pytz.timezone('US/Eastern')
    
    fe = MockFeatureEngineer()
    
    # Test with naive datetime (should work)
    print("\nTest 1: Naive datetime")
    naive_time = datetime.now().replace(tzinfo=None)
    print(f"Input: {naive_time}, tzinfo={naive_time.tzinfo}")
    try:
        result = fe.create_temporal_features(naive_time)
        print(f"✓ Success: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test with aware datetime (should fail or be handled by patch)
    print("\nTest 2: Aware datetime") 
    aware_time = datetime.now(timezone.utc)
    print(f"Input: {aware_time}, tzinfo={aware_time.tzinfo}")
    try:
        result = fe.create_temporal_features(aware_time)
        print(f"✓ Success (patch handled it): {result}")
    except Exception as e:
        print(f"✗ Error (patch didn't handle it): {e}")
        
except Exception as e:
    print(f"Could not test: {e}")

print("\n=== Debug script complete ===")
