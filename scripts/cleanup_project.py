#!/usr/bin/env python3
"""
Magic8 Trading System Cleanup Script
Safely backs up and reorganizes project files
"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path("/Users/jt/magic8")
BACKUP_DIR = PROJECT_ROOT / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Files to keep (essential files)
ESSENTIAL_FILES = {
    "Magic8-Companion": {
        "keep_in_root": [
            ".env",
            ".env.example", 
            ".env.simplified.example",
            ".gitignore",
            "INTEGRATION_GUIDE.md",
            "README.md",
            "README_SIMPLIFIED.md",
            "requirements.txt",
            "requirements_simplified.txt",
            "setup_spx_gex.py"  # Keep - it's a setup script, not duplicate
        ],
        "keep_folders": [
            "magic8_companion",
            "data",
            "docs",
            "integration"
        ],
        "move_to_tests": [
            "test_simplified.py",
            "test_live_data.py"
        ]
    },
    "DiscordTrading": {
        "keep_in_root": [
            ".env",
            ".env.example",
            ".gitignore",
            "CHANGELOG.md",
            "README.md",
            "config.py",
            "config.yaml",
            "discord_trading_bot.py",
            "order_manager.py",
            "requirements.txt",
            "trading_strategies.py",
            "magic8_integration.py",
            "test_integration.py"
        ],
        "keep_folders": [
            "dce",
            "docs",
            "logs",
            "tests"
        ]
    }
}

def create_backup():
    """Create a backup of the entire project"""
    print(f"📦 Creating backup at: {BACKUP_DIR}")
    if os.path.exists(PROJECT_ROOT):
        shutil.copytree(PROJECT_ROOT, BACKUP_DIR, 
                       ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git'))
        print("✅ Backup created successfully")
    else:
        print(f"❌ Project root not found: {PROJECT_ROOT}")
        return False
    return True

def cleanup_magic8_companion():
    """Clean up Magic8-Companion directory"""
    magic8_path = PROJECT_ROOT / "Magic8-Companion"
    if not magic8_path.exists():
        print("❌ Magic8-Companion directory not found")
        return
    
    print("\n🧹 Cleaning Magic8-Companion...")
    
    # Create tests directory if it doesn't exist
    tests_dir = magic8_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    # Move test files to tests directory
    for test_file in ESSENTIAL_FILES["Magic8-Companion"]["move_to_tests"]:
        src = magic8_path / test_file
        dst = tests_dir / test_file
        if src.exists() and not dst.exists():
            shutil.move(str(src), str(dst))
            print(f"  ➡️  Moved {test_file} to tests/")
    
    # Remove any files not in the essential list
    removed_count = 0
    for item in magic8_path.iterdir():
        if item.is_file():
            if item.name not in ESSENTIAL_FILES["Magic8-Companion"]["keep_in_root"]:
                if item.name not in ESSENTIAL_FILES["Magic8-Companion"]["move_to_tests"]:
                    print(f"  🗑️  Removing: {item.name}")
                    item.unlink()
                    removed_count += 1
        elif item.is_dir():
            if item.name not in ESSENTIAL_FILES["Magic8-Companion"]["keep_folders"]:
                if item.name not in ['.git', '__pycache__', '.env']:
                    print(f"  🗑️  Removing directory: {item.name}")
                    shutil.rmtree(item)
                    removed_count += 1
    
    print(f"✅ Magic8-Companion cleaned: {removed_count} items removed")

def cleanup_discord_trading():
    """Clean up DiscordTrading directory"""
    discord_path = PROJECT_ROOT / "DiscordTrading"
    if not discord_path.exists():
        print("❌ DiscordTrading directory not found")
        return
    
    print("\n🧹 Cleaning DiscordTrading...")
    
    # Remove any files not in the essential list
    removed_count = 0
    for item in discord_path.iterdir():
        if item.is_file():
            if item.name not in ESSENTIAL_FILES["DiscordTrading"]["keep_in_root"]:
                print(f"  🗑️  Removing: {item.name}")
                item.unlink()
                removed_count += 1
        elif item.is_dir():
            if item.name not in ESSENTIAL_FILES["DiscordTrading"]["keep_folders"]:
                if item.name not in ['.git', '__pycache__', '.env']:
                    print(f"  🗑️  Removing directory: {item.name}")
                    shutil.rmtree(item)
                    removed_count += 1
    
    print(f"✅ DiscordTrading cleaned: {removed_count} items removed")

def cleanup_testing_folder():
    """Remove the testing folder if it exists"""
    testing_path = PROJECT_ROOT / "testing"
    if testing_path.exists():
        print("\n🧹 Removing testing/ folder...")
        shutil.rmtree(testing_path)
        print("✅ testing/ folder removed")

def create_summary():
    """Create a summary of the cleanup"""
    summary = {
        "cleanup_date": datetime.now().isoformat(),
        "backup_location": str(BACKUP_DIR),
        "project_structure": {
            "Magic8-Companion": {
                "main_app": "magic8_companion/main_simplified.py",
                "tests": [
                    "tests/test_simplified.py",
                    "tests/test_live_data.py",
                    "tests/test_*.py (unit tests)"
                ],
                "data": "data/recommendations.json"
            },
            "DiscordTrading": {
                "main_bot": "discord_trading_bot.py",
                "integration": "magic8_integration.py",
                "test": "test_integration.py"
            }
        }
    }
    
    summary_path = PROJECT_ROOT / "cleanup_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📄 Cleanup summary saved to: {summary_path}")

def main():
    """Main cleanup function"""
    print("🚀 Magic8 Trading System Cleanup")
    print("================================\n")
    
    # Create backup first
    if not create_backup():
        return
    
    # Cleanup each component
    cleanup_magic8_companion()
    cleanup_discord_trading()
    cleanup_testing_folder()
    
    # Create summary
    create_summary()
    
    print("\n✅ Cleanup complete!")
    print(f"\n💡 Backup saved to: {BACKUP_DIR}")
    print("\nNext steps:")
    print("1. Review the changes")
    print("2. Test the system with the consolidated structure")
    print("3. Delete the backup once confirmed everything works")

if __name__ == "__main__":
    main()
