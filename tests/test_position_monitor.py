import pytest
from magic8_companion.modules.position_monitor import check_exit_signals

# Sample position data structures
# Note: The position monitor logic (and thus these tests) might need to be updated
# if the actual DB position structure (from db_client.py) differs significantly
# or if position details like 'center_strike', 'short_put_strike' etc.
# are not directly available and need parsing from 'strikes_info'.
# For now, these tests assume these fields are present in the position dict.
# The `max_position_loss` is taken from `settings` (default 2000).

butterfly_pos = {
    'combo_type': 'butterfly', 'strikes_info': 'C4950/C5000/C5050', # Example
    'center_strike': 5000, 'wing_width': 50,
    'current_pnl': -100, 'symbol': 'SPX' # Changed 'unrealized_pnl' to 'current_pnl'
}
iron_condor_pos = {
    'combo_type': 'iron_condor', 'strikes_info': 'P4900/P4950_C5050/C5100', # Example
    'short_put_strike': 4950, 'short_call_strike': 5050, # Assuming these are the short strikes
    'current_pnl': -50, 'symbol': 'SPX'
}
vertical_put_pos_bull = {
    'combo_type': 'vertical', 'direction': 'bull',
    'strikes_info': 'P4950/P4900', # Long P4950, Short P4900
    'current_pnl': 20, 'symbol': 'SPX'
}
vertical_call_pos_bear = {
    'combo_type': 'vertical', 'direction': 'bear',
    'strikes_info': 'C5050/C5100', # Short C5050, Long C5100
    'current_pnl': 10, 'symbol': 'SPX'
}

# Sample Magic8 data
magic8_base = {
    'spot_price': 5000, 'targets': [4980, 5020], 'trend': 'neutral'
}

# Test cases: (position_data, magic8_market_data, expected_trigger_types_or_empty_list)
exit_signal_test_cases = [
    # Butterfly Tests
    # Assuming 'center_strike' is available directly in the position dict
    (butterfly_pos, {**magic8_base, 'spot_price': 5040}, ['POSITION_DRIFT']),
    (butterfly_pos, {**magic8_base, 'spot_price': 4960}, ['POSITION_DRIFT']),
    (butterfly_pos, {**magic8_base, 'spot_price': 5010}, []),
    # Assuming 'targets' are [lower_target, upper_target]
    (butterfly_pos, {**magic8_base, 'targets': [5060, 5080]}, ['RANGE_SHIFT']),
    (butterfly_pos, {**magic8_base, 'targets': [4900, 4950]}, ['RANGE_SHIFT']),
    (butterfly_pos, {**magic8_base, 'targets': [4950, 5050]}, []),

    # Iron Condor Tests
    # Assuming 'short_put_strike' and 'short_call_strike' are available
    (iron_condor_pos, {**magic8_base, 'spot_price': 4940}, ['POSITION_DRIFT']), # spot (4940) <= short_put_strike (4950)
    (iron_condor_pos, {**magic8_base, 'spot_price': 5060}, ['POSITION_DRIFT']), # spot (5060) >= short_call_strike (5050)
    (iron_condor_pos, {**magic8_base, 'spot_price': 5000}, []),

    # Vertical Spread Tests (Trend Reversal)
    # Assuming 'direction' is in position dict
    (vertical_put_pos_bull, {**magic8_base, 'trend': 'down'}, ['TREND_REVERSAL']),
    (vertical_put_pos_bull, {**magic8_base, 'trend': 'up'}, []),
    (vertical_call_pos_bear, {**magic8_base, 'trend': 'up'}, ['TREND_REVERSAL']),
    (vertical_call_pos_bear, {**magic8_base, 'trend': 'down'}, []),

    # Loss Limit Tests (using settings.max_position_loss which defaults to 2000)
    ({**butterfly_pos, 'current_pnl': -2001}, magic8_base, ['LOSS_LIMIT']),
    ({**iron_condor_pos, 'current_pnl': -2500}, magic8_base, ['LOSS_LIMIT']),
    ({**vertical_put_pos_bull, 'current_pnl': -2000.00}, magic8_base, ['LOSS_LIMIT']),
    ({**vertical_put_pos_bull, 'current_pnl': -1999.99}, magic8_base, []),

    # Multiple triggers
    ({**butterfly_pos, 'current_pnl': -2001, 'center_strike': 5000}, {**magic8_base, 'spot_price': 5040}, ['POSITION_DRIFT', 'LOSS_LIMIT']),
]

@pytest.mark.parametrize("position, magic8_data, expected_triggers", exit_signal_test_cases)
def test_check_exit_signals_detailed(position, magic8_data, expected_triggers):
    # Ensure the position dictionary has 'combo_type' as check_exit_signals expects 'type'
    # This is a temporary adaptation if the test data uses 'combo_type' from DB schema
    # and the function expects 'type'.
    pos_for_func = position.copy()
    if 'combo_type' in pos_for_func and 'type' not in pos_for_func:
        pos_for_func['type'] = pos_for_func.pop('combo_type')

    signals = check_exit_signals(pos_for_func, magic8_data)
    triggered_reasons = sorted([s['trigger'] for s in signals])
    assert triggered_reasons == sorted(expected_triggers)

def test_check_exit_signals_no_triggers():
    safe_pos = {**butterfly_pos, 'current_pnl': -10}
    # Adapt for function if needed
    if 'combo_type' in safe_pos and 'type' not in safe_pos:
        safe_pos['type'] = safe_pos.pop('combo_type')

    safe_m8 = {**magic8_base, 'spot_price': 5005, 'targets': [4980, 5030], 'trend': 'neutral'}
    signals = check_exit_signals(safe_pos, safe_m8)
    assert len(signals) == 0

# Test for vertical with missing direction (should not error, but might not trigger trend reversal)
def test_check_exit_signals_vertical_missing_direction():
    pos_no_direction = {
        'type': 'vertical', 'strikes_info': 'P4950/P4900',
        'current_pnl': 20, 'symbol': 'SPX'
        # No 'direction'
    }
    signals = check_exit_signals(pos_no_direction, {**magic8_base, 'trend': 'down'})
    # Depending on implementation, this might return empty or a specific warning.
    # For now, just ensure it doesn't crash and check no trend reversal if direction is key.
    assert not any(s['trigger'] == 'TREND_REVERSAL' for s in signals)

# Test for position type not handled (e.g. 'stock')
def test_check_exit_signals_unknown_type():
    unknown_pos = {'type': 'stock', 'symbol': 'AAPL', 'current_pnl': 100}
    signals = check_exit_signals(unknown_pos, magic8_base)
    assert len(signals) == 0 # Expect no signals for unmonitored types, or specific handling
