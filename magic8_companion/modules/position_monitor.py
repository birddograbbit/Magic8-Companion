from typing import Dict, List


def check_exit_signals(position: Dict, magic8_data: Dict) -> List[Dict]:
    """Check if position should be exited"""
    spot = magic8_data.get('spot_price', 0)
    predicted_range = magic8_data.get('targets', [0, 0])

    exit_signals = []

    if position['type'] == 'butterfly':
        center = position.get('center_strike', 0)
        width = position.get('wing_width', 0)
        distance = abs(spot - center)
        if distance > (width * 0.75):
            exit_signals.append({
                'trigger': 'POSITION_DRIFT',
                'reason': f'Spot {spot} > 75% from center {center}'
            })
        if not (predicted_range[0] <= center <= predicted_range[1]):
            exit_signals.append({
                'trigger': 'RANGE_SHIFT',
                'reason': f'Range {predicted_range} excludes center {center}'
            })
    elif position['type'] == 'iron_condor':
        sp = position.get('short_put_strike', 0)
        sc = position.get('short_call_strike', 0)
        if spot <= sp * 1.02 or spot >= sc * 0.98:
            exit_signals.append({
                'trigger': 'POSITION_DRIFT',
                'reason': 'Spot approaching short strikes'
            })
    elif position['type'] == 'vertical':
        direction = position.get('direction')
        trend = magic8_data.get('trend', '').lower()
        if (direction == 'bull' and trend == 'down') or (direction == 'bear' and trend == 'up'):
            exit_signals.append({
                'trigger': 'TREND_REVERSAL',
                'reason': f'Position {direction} vs trend {trend}'
            })

    if position.get('unrealized_pnl', 0) <= -2000:
        exit_signals.append({
            'trigger': 'LOSS_LIMIT',
            'reason': f"Loss {abs(position['unrealized_pnl'])} exceeds limit"
        })

    return exit_signals
