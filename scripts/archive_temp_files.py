#!/usr/bin/env python3
"""
Archive temporary and duplicate files to clean up the repository.
This script moves identified temporary, duplicate, and old files to an archive folder.
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

# Define files to archive with their destination folders
FILES_TO_ARCHIVE = {
    "archive/temp-scripts": [
        "scripts/cleanup_project.py",
        "scripts/final_cleanup.sh",
        "scripts/remove_empty_files.py",
        "scripts/make_executable.sh",
        "scripts/setup_enhanced.sh"
    ],
    "archive/old-docs": [
        "IBKR_SUMMARY.md",
        "README_SIMPLIFIED.md", 
        "CLEANUP_INSTRUCTIONS.md",
        "PR_DESCRIPTION.md"
    ],
    "archive/old-config": [
        ".env.simplified.example",
        "requirements_simplified.txt"
    ],
    "archive/old-code": [
        "setup_spx_gex.py"  # Check if exists
    ]
}


def create_archive_structure():
    """Create the archive directory structure."""
    for archive_dir in FILES_TO_ARCHIVE.keys():
        Path(archive_dir).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {archive_dir}")


def archive_files():
    """Move files to their archive locations."""
    moved_files = []
    not_found = []
    
    for archive_dir, files in FILES_TO_ARCHIVE.items():
        for file_path in files:
            src = Path(file_path)
            
            if src.exists():
                # Create destination path
                dst = Path(archive_dir) / src.name
                
                # Move the file
                try:
                    shutil.move(str(src), str(dst))
                    moved_files.append((file_path, archive_dir))
                    print(f"✓ Archived: {file_path} → {archive_dir}/")
                except Exception as e:
                    print(f"✗ Error moving {file_path}: {e}")
            else:
                not_found.append(file_path)
    
    return moved_files, not_found


def create_archive_readme():
    """Create a README in the archive directory explaining the contents."""
    readme_content = """# Archive Directory

This directory contains files that were moved from the active repository during cleanup.
These files are preserved for historical reference but are no longer actively used.

## Directory Structure

- **temp-scripts/**: One-time cleanup and utility scripts
- **old-docs/**: Duplicate or temporary documentation files
- **old-config/**: Duplicate configuration examples
- **old-code/**: Old or superseded code files

## Archived Files

### Temporary Scripts
- cleanup_project.py - One-time project cleanup script
- final_cleanup.sh - Final cleanup bash script
- remove_empty_files.py - Utility to remove empty files
- make_executable.sh - Script to set executable permissions
- setup_enhanced.sh - Old enhanced setup script

### Old Documentation
- IBKR_SUMMARY.md - Summary of IBKR integration (superseded by IBKR_INTEGRATION.md)
- README_SIMPLIFIED.md - Simplified README (superseded by main README.md)
- CLEANUP_INSTRUCTIONS.md - Temporary cleanup instructions
- PR_DESCRIPTION.md - Pull request description template

### Old Configuration
- .env.simplified.example - Simplified env example (superseded by .env.example)
- requirements_simplified.txt - Simplified requirements (superseded by requirements.txt)

### Old Code
- setup_spx_gex.py - Old SPX GEX setup script

## Note
These files are kept for reference only. The active, maintained versions of 
documentation and configuration are in the repository root.
"""
    
    readme_path = Path("archive/README.md")
    readme_path.write_text(readme_content)
    print(f"✓ Created archive README: {readme_path}")


def main():
    """Main function to perform the archiving."""
    print("🧹 Starting repository cleanup...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Create archive structure
    print("\n📂 Creating archive directories...")
    create_archive_structure()
    
    # Archive files
    print("\n📦 Archiving files...")
    moved_files, not_found = archive_files()
    
    # Create archive README
    print("\n📝 Creating archive documentation...")
    create_archive_readme()
    
    # Summary
    print("\n✨ Cleanup Summary:")
    print(f"  ✓ Files archived: {len(moved_files)}")
    print(f"  ✗ Files not found: {len(not_found)}")
    
    if not_found:
        print("\n⚠️  Files not found (may already be archived or deleted):")
        for file in not_found:
            print(f"  - {file}")
    
    print("\n✅ Cleanup complete!")
    print("\n💡 Next steps:")
    print("  1. Review the archived files in the 'archive/' directory")
    print("  2. Commit the changes: git add -A && git commit -m 'Archive temporary and duplicate files'")
    print("  3. Update any documentation that referenced the archived files")


if __name__ == "__main__":
    main()
