#!/bin/bash
# Start Magic8-Companion with Gamma Enhancement

echo "Starting Magic8-Companion (Enhanced Mode)..."
echo "==========================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating .venv..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating venv..."
    source venv/bin/activate
fi

# Use python3 if python is not available
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "Error: No Python interpreter found!"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Ensure enhanced mode is set
export M8C_SYSTEM_COMPLEXITY=enhanced
export M8C_ENABLE_ENHANCED_GEX=true

# Run Magic8
$PYTHON_CMD -m magic8_companion

# Keep window open on error
read -p "Press Enter to exit..."
