I'll check the Magic8-Companion repository to understand the current gamma implementation and create a fix plan.
# Magic8-Companion Call Wall Fix Plan

## Executive Summary

The gamma analysis module in Magic8-Companion has the same call wall detection bug that was identified in MLOptionTrading. This plan outlines the steps to fix the issue and ensure accurate gamma exposure calculations.

## Issue Details

### The Bug
The `_find_key_levels()` method incorrectly searches for positive GEX values when identifying call walls:
```python
if len(call_df) > 0 and len(call_df[call_df['gex'] > 0]) > 0:
    call_wall = call_df.loc[call_df['gex'].idxmax(), 'strike']
```

However, since dealers are typically short calls, call GEX values are negative. This causes the call wall to default to `spot + 50` instead of finding the actual resistance level.

### Root Cause
- Call GEX is calculated as negative: `call_gex = -call_gamma * opt['call_oi'] * self.spot_multiplier * spot_price`
- The code looks for strikes with positive GEX above spot (which rarely exist)
- Put wall logic has the opposite issue (looking for negative when puts contribute positive GEX)

## The Fix

### Corrected Implementation
Based on industry standards and research, the fix identifies:
- **Call Wall**: Strike with highest positive NET GEX above spot (resistance)
- **Put Wall**: Strike with most negative NET GEX below spot (support)

```python
def _find_key_levels(self, strike_gex: Dict[float, float], spot: float) -> Dict:
    """
    Identify gamma walls and flip point
    
    Note: strike_gex contains NET gamma exposure (calls + puts combined)
    """
    if not strike_gex:
        return {
            'gamma_flip': spot,
            'call_wall': spot + 50,
            'put_wall': spot - 50,
            'expected_move': 0.01,
            'spot_vs_flip': 0
        }

    df = pd.DataFrame(list(strike_gex.items()),
                     columns=['strike', 'gex'])
    df = df.sort_values('strike')
    df['cumsum_gex'] = df['gex'].cumsum()

    # Gamma flip point (where cumulative GEX crosses zero)
    if len(df[df['cumsum_gex'] >= 0]) > 0 and len(df[df['cumsum_gex'] < 0]) > 0:
        flip_idx = df['cumsum_gex'].abs().idxmin()
        gamma_flip = df.loc[flip_idx, 'strike']
    else:
        gamma_flip = spot

    # Call wall: strike with highest positive NET GEX above spot
    call_df = df[df['strike'] > spot]
    if len(call_df) > 0:
        positive_gex = call_df[call_df['gex'] > 0]
        if len(positive_gex) > 0:
            call_wall = positive_gex.loc[positive_gex['gex'].idxmax(), 'strike']
        else:
            call_wall = spot + 50
    else:
        call_wall = spot + 50

    # Put wall: strike with most negative NET GEX below spot
    put_df = df[df['strike'] < spot]
    if len(put_df) > 0:
        negative_gex = put_df[put_df['gex'] < 0]
        if len(negative_gex) > 0:
            put_wall = negative_gex.loc[negative_gex['gex'].idxmin(), 'strike']
        else:
            put_wall = spot - 50
    else:
        put_wall = spot - 50

    # Expected move based on gamma distribution
    expected_move = abs(call_wall - put_wall) / spot

    return {
        'gamma_flip': gamma_flip,
        'call_wall': call_wall,
        'put_wall': put_wall,
        'expected_move': expected_move,
        'spot_vs_flip': (spot - gamma_flip) / spot if spot != 0 else 0
    }
```

## Implementation Plan

### 1. Create Feature Branch
```bash
cd Magic8-Companion
git checkout main
git pull origin main
git checkout -b fix/gamma-call-wall-detection
```

### 2. Apply the Fix
- Edit `magic8_companion/analysis/gamma/gamma_exposure.py`
- Replace the `_find_key_levels()` method with the corrected implementation
- Add detailed comments explaining the NET GEX logic

### 3. Add Unit Tests
Create comprehensive tests in `tests/test_gamma_levels.py`:
```python
def test_call_wall_detection_with_negative_call_gex():
    """Test that call wall is correctly identified when calls have negative GEX"""
    # Test implementation
    
def test_put_wall_detection_with_positive_put_gex():
    """Test that put wall is correctly identified when puts have positive GEX"""
    # Test implementation
```

### 4. Integration Testing
Test with the UnifiedComboScorer to ensure gamma adjustments work correctly:
```python
# Test gamma integration
scorer = UnifiedComboScorer(complexity='enhanced')
results = scorer.score_combo_types(market_data, 'SPX')
# Verify gamma adjustments are applied correctly
```

### 5. Real Market Data Testing
- Run gamma analysis on live market data
- Compare results with industry gamma tools
- Verify call/put walls align with expected resistance/support levels

## Deployment Strategy

### Phase 1: Development Testing (1-2 days)
1. Apply fix in feature branch
2. Run all unit tests
3. Manual testing with sample data

### Phase 2: Staging Environment (2-3 days)
1. Deploy to staging environment
2. Run parallel comparison:
   - Old logic vs New logic
   - Log differences for analysis
3. Verify gamma_adjustments.json output

### Phase 3: Production Deployment (1 day)
1. Create PR with detailed description
2. Code review by team
3. Merge to main branch
4. Deploy to production
5. Monitor for 24-48 hours

## Monitoring Plan

### Key Metrics to Track
1. **Call Wall Accuracy**: Compare identified levels with actual price resistance
2. **Put Wall Accuracy**: Compare identified levels with actual price support
3. **Gamma Flip Stability**: Ensure flip point calculations remain stable
4. **Score Adjustments**: Monitor changes in strategy scores

### Alert Conditions
- Call wall defaults to spot + 50 more than 10% of the time
- Put wall defaults to spot - 50 more than 10% of the time
- Gamma adjustments exceed ±50 points (indicates potential issue)

## Rollback Plan

### If Issues Detected
1. Revert to previous commit: `git revert <commit-hash>`
2. Deploy hotfix immediately
3. Investigate issue in development environment
4. Re-implement fix with corrections

### Backup Strategy
- Tag current version before deployment: `git tag pre-gamma-fix-v1.0`
- Keep 7 days of gamma_adjustments.json history
- Document all changes in CHANGELOG.md

## Success Criteria

The fix is considered successful when:
1. ✅ Call walls are identified at strikes with actual dealer resistance
2. ✅ Put walls are identified at strikes with actual dealer support
3. ✅ Gamma signals align with market microstructure
4. ✅ Strategy scores improve in accuracy
5. ✅ No regression in existing functionality

## Timeline

- **Day 1-2**: Implementation and unit testing
- **Day 3-4**: Staging deployment and parallel testing
- **Day 5**: Production deployment
- **Day 6-7**: Monitoring and validation

## Additional Recommendations

1. **Documentation Update**: Update the gamma analysis documentation to explain NET GEX concept
2. **Visualization**: Consider adding gamma profile visualization to verify wall identification
3. **Configuration**: Add option to use alternative wall detection methods (absolute GEX vs directional)
4. **Alerts**: Implement Discord notifications when significant gamma walls are breached

This fix will ensure Magic8-Companion correctly identifies key gamma levels, improving the accuracy of trading signals and strategy selection.