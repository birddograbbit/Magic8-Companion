#!/bin/bash
# Make test scripts executable
chmod +x scripts/test_enhanced_indicators.py
chmod +x scripts/test_real_market_data.py

echo "Scripts are now executable!"
echo ""
echo "To test with real market data:"
echo "  ./scripts/test_real_market_data.py"
echo ""
echo "To test with mock data:"
echo "  ./scripts/test_enhanced_indicators.py"
