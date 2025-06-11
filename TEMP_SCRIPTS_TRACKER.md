# Temporary Test Scripts Tracker

This file tracks all temporary test scripts created during SPX debugging.
These can be removed once the issues are resolved.

## Scripts to Clean Up:

1. **scripts/diagnose_spx_options.py** - Created to diagnose SPX option chain retrieval methods
2. **scripts/test_spx_spxw.py** - Quick test for SPXW symbol mapping
3. **scripts/verify_spx_fix.py** - Verification script for SPX fix
4. **scripts/inspect_ticker_attributes.py** - Inspect Ticker object attributes (to be created)

## Cleanup Command:
```bash
# Remove all temporary test scripts
rm scripts/diagnose_spx_options.py scripts/test_spx_spxw.py scripts/verify_spx_fix.py scripts/inspect_ticker_attributes.py
```

## Notes:
- These scripts were created to debug IBKR SPX option chain issues
- They can be safely removed after confirming the main functionality works
- The fixes have been applied to the main code in `magic8_companion/modules/ibkr_market_data.py`
