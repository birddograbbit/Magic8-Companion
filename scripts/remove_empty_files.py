#!/usr/bin/env python3
"""
Quick cleanup script to remove empty test files from root
Can be run from any directory
"""
import os
from pathlib import Path

def main():
    """Remove empty test files from root directory"""
    # Get the Magic8-Companion root directory
    # This script is in Magic8-Companion/scripts/
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"Looking for files in: {project_root}")
    
    files_to_remove = [
        "test_simplified.py",
        "test_live_data.py"
    ]
    
    removed = []
    for filename in files_to_remove:
        filepath = project_root / filename
        if filepath.exists() and filepath.stat().st_size == 0:
            filepath.unlink()
            removed.append(filename)
            print(f"✅ Removed empty file: {filename}")
        elif filepath.exists():
            print(f"⚠️  File not empty ({filepath.stat().st_size} bytes), skipping: {filename}")
        else:
            print(f"ℹ️  File not found: {filename}")
    
    if removed:
        print(f"\n✅ Cleanup complete! Removed {len(removed)} empty files.")
        print("\nYour project structure is now clean. The test files are properly located in the tests/ folder.")
        print("\nNow commit these changes:")
        print(f"cd {project_root}")
        print("git add -A")
        print('git commit -m "Remove empty test files from root"')
        print("git push origin main")
    else:
        print("\n✅ No cleanup needed - project structure is already clean!")

if __name__ == "__main__":
    main()
