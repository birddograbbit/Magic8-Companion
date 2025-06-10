#!/usr/bin/env python3
"""
Quick cleanup script to remove empty test files from root
Run this after pulling from GitHub
"""
import os
from pathlib import Path

def main():
    """Remove empty test files from root directory"""
    files_to_remove = [
        "test_simplified.py",
        "test_live_data.py"
    ]
    
    removed = []
    for filename in files_to_remove:
        filepath = Path(filename)
        if filepath.exists() and filepath.stat().st_size == 0:
            filepath.unlink()
            removed.append(filename)
            print(f"✅ Removed empty file: {filename}")
        elif filepath.exists():
            print(f"⚠️  File not empty, skipping: {filename}")
        else:
            print(f"ℹ️  File not found: {filename}")
    
    if removed:
        print(f"\n✅ Cleanup complete! Removed {len(removed)} empty files.")
        print("\nYour project structure is now clean. The test files are properly located in the tests/ folder.")
    else:
        print("\n✅ No cleanup needed - project structure is already clean!")

if __name__ == "__main__":
    main()
