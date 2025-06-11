# SPY Half-Dollar Strikes Fix

## Issue
SPY options with half-dollar strikes (587.5, 592.5, 597.5, 602.5, 607.5) fail to qualify with error:
```
Error 200, reqId XXX: No security definition has been found for the request
```

## Investigation Results

### Current Configuration
- SPY is configured to use exchange='SMART' in the exchange_map
- Trading class is set to 'SPY'
- The option chains are found but specific half-dollar strikes fail qualification

### Root Cause
SPY options trade on multiple exchanges:
- CBOE - Typically has all strikes including half-dollars
- NASDAQOM - May not have all half-dollar strikes
- SMART - Should route to best exchange but may fail for some strikes

When using a specific exchange (NASDAQOM in the error log), not all strikes may be available.

## Proposed Solutions

### Solution 1: Use SMART Exchange (Recommended)
Let IB's SMART routing find the best exchange for each strike:
```python
# Already configured correctly in exchange_map
'SPY': 'SMART'
```

### Solution 2: Use CBOE for SPY
CBOE typically has the most complete option chain:
```python
# Update exchange_map
'SPY': 'CBOE'
```

### Solution 3: Fallback Logic for Failed Strikes
When a strike fails to qualify on the primary exchange, try alternate exchanges:
```python
async def qualify_with_fallback(self, contract, exchanges=['SMART', 'CBOE', 'NASDAQOM']):
    """Try to qualify contract on multiple exchanges."""
    for exchange in exchanges:
        try:
            contract.exchange = exchange
            qualified = await self.ib.qualifyContractsAsync(contract)
            if qualified and qualified[0].conId:
                return qualified[0]
        except:
            continue
    return None
```

## Implementation Notes

The current code is using the exchange from the option chain data:
```python
# From the code
exchange=selected_chain.exchange
```

This means it's using whatever exchange the chain reports (NASDAQOM in the error case), rather than the configured exchange map. This might be the issue.

## Recommended Fix

Modify the option contract creation to prefer SMART routing for SPY:
```python
# For SPY, always use SMART to ensure all strikes are accessible
if original_symbol == 'SPY':
    exchange = 'SMART'
else:
    exchange = selected_chain.exchange
```

This ensures SPY options use IB's smart routing to find the best exchange for each strike.

### June 11 Update

The code now implements a `qualify_contract_with_fallback` helper that retries
qualification across multiple exchanges if the initial attempt fails. For SPY
the sequence is `SMART`, `CBOE`, `AMEX`, then `ISE`.  The logs show which
exchange ultimately succeeds so we can track where half-dollar strikes are
available.  This fallback removes the `No security definition` warnings during
testing.
