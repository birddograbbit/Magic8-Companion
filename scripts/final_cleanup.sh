#!/bin/bash
# Final cleanup script for Magic8-Companion
# This script removes empty test files and ensures clean structure

echo "🧹 Magic8-Companion Final Cleanup"
echo "================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Remove empty test files from root if they exist
echo ""
echo "Removing empty test files from root..."

if [ -f "test_simplified.py" ] && [ ! -s "test_simplified.py" ]; then
    rm test_simplified.py
    echo "✅ Removed empty test_simplified.py"
else
    echo "ℹ️  test_simplified.py not found or not empty"
fi

if [ -f "test_live_data.py" ] && [ ! -s "test_live_data.py" ]; then
    rm test_live_data.py
    echo "✅ Removed empty test_live_data.py"
else
    echo "ℹ️  test_live_data.py not found or not empty"
fi

# Verify the files are in the tests folder
echo ""
echo "Verifying test files in tests/ folder..."

if [ -f "tests/test_simplified.py" ] && [ -s "tests/test_simplified.py" ]; then
    echo "✅ tests/test_simplified.py exists with content"
else
    echo "❌ tests/test_simplified.py missing or empty!"
fi

if [ -f "tests/test_live_data.py" ] && [ -s "tests/test_live_data.py" ]; then
    echo "✅ tests/test_live_data.py exists with content"
else
    echo "❌ tests/test_live_data.py missing or empty!"
fi

# Show current structure
echo ""
echo "Current project structure:"
echo "========================="
ls -la | grep -E "(test_|tests|scripts)"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Commit these changes locally:"
echo "   git add -A"
echo "   git commit -m 'Remove empty test files from root'"
echo "   git push origin main"
echo ""
echo "2. Run tests with:"
echo "   python scripts/test_runner.py"
