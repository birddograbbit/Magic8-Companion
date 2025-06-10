#!/bin/bash

# Magic8-Companion Enhanced Setup Script
# Ship-fast approach: Use production PyPI packages, reference GitHub repos for methodology

echo "🚀 Setting up Magic8-Companion Enhanced Indicators..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the Magic8-Companion root directory"
    exit 1
fi

# Step 1: Update pip
echo -e "${BLUE}📦 Updating pip...${NC}"
python -m pip install --upgrade pip

# Step 2: Install enhanced requirements
echo -e "${BLUE}📦 Installing enhanced dependencies...${NC}"
pip install -r requirements.txt

# Step 3: Create directories for wrapper modules
echo -e "${BLUE}📁 Creating wrapper module directories...${NC}"
mkdir -p magic8_companion/wrappers
mkdir -p magic8_companion/data/cache
mkdir -p reference_repos

# Step 4: Download reference implementations (optional, for methodology only)
echo -e "${YELLOW}📚 Download reference repositories for methodology? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}📥 Cloning reference repositories...${NC}"
    cd reference_repos
    
    # SPX Gamma Exposure reference
    if [ ! -d "SPX-Gamma-Exposure" ]; then
        git clone https://github.com/jensolson/SPX-Gamma-Exposure.git
        echo -e "${GREEN}✓ SPX-Gamma-Exposure cloned${NC}"
    fi
    
    # 0DTE Trader reference
    if [ ! -d "0dte-trader" ]; then
        git clone https://github.com/aicheung/0dte-trader.git
        echo -e "${GREEN}✓ 0dte-trader cloned${NC}"
    fi
    
    cd ..
fi

# Step 5: Create __init__.py files for wrappers
echo -e "${BLUE}📝 Creating wrapper module files...${NC}"

# Create __init__.py for wrappers
cat > magic8_companion/wrappers/__init__.py << 'EOF'
"""
Wrapper modules for production-ready external libraries.
Ship-fast approach: Simple interfaces to mature systems.
"""
from .greeks_wrapper import GreeksWrapper
from .gex_wrapper import GammaExposureWrapper
from .volume_wrapper import VolumeOIWrapper

__all__ = ['GreeksWrapper', 'GammaExposureWrapper', 'VolumeOIWrapper']
EOF

# Step 6: Verify installation
echo -e "${BLUE}🔍 Verifying installations...${NC}"
python -c "import py_vollib_vectorized; print('✓ py_vollib_vectorized installed')"
python -c "import numpy; print('✓ numpy installed')"
python -c "import pandas; print('✓ pandas installed')"
python -c "import scipy; print('✓ scipy installed')"
python -c "import aiohttp; print('✓ aiohttp installed')"

# Step 7: Create example .env for enhanced features
if [ ! -f ".env.enhanced" ]; then
    echo -e "${BLUE}📝 Creating example .env.enhanced file...${NC}"
    cat > .env.enhanced << 'EOF'
# Enhanced Indicators Configuration
ENABLE_GREEKS=true
ENABLE_ADVANCED_GEX=true
ENABLE_VOLUME_ANALYSIS=true

# Greeks Settings
RISK_FREE_RATE=0.05
GREEKS_CACHE_TTL=300  # 5 minutes

# Gamma Exposure Settings
GEX_CALCULATION_METHOD=net  # net or gross
GEX_STRIKE_RANGE=50  # strikes above/below spot

# Volume/OI Settings
UNUSUAL_ACTIVITY_THRESHOLD=3.0
MIN_OPEN_INTEREST=100

# Performance Settings
USE_CACHE=true
CACHE_DIR=./magic8_companion/data/cache
MAX_WORKERS=4

# Keep existing settings
USE_MOCK_DATA=true
MIN_RECOMMENDATION_SCORE=70
EOF
    echo -e "${GREEN}✓ Created .env.enhanced${NC}"
fi

echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy .env.enhanced to .env to enable enhanced features"
echo "2. Run tests: python -m pytest tests/"
echo "3. Start with mock data: python -m magic8_companion.main_simplified"
echo ""
echo -e "${BLUE}Ship-fast tip: Start with Greeks integration first, then add GEX and Volume/OI${NC}"
