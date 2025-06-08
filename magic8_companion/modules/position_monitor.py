from typing import Dict, List
from ..utils.position_parser import map_db_position_to_monitor_format


def check_exit_signals(position: Dict, magic8_data: Dict) -> List[Dict]:
    """
    Check if position should be exited.
    
    Accepts positions in either database format or monitor format.
    Automatically converts DB format using position parser.
    
    Args:
        position: Position dict (from DB or already formatted)
        magic8_data: Latest Magic8 prediction data
        
    Returns:
        List of exit signals with trigger and reason
    """
    # Convert DB position format to monitor format if needed
    if 'combo_type' in position and 'type' not in position:
        position = map_db_position_to_monitor_format(position)
    
    spot = magic8_data.get('spot_price', 0)
    predicted_range = magic8_data.get('targets', [0, 0])
    
    exit_signals = []
    
    # Get position type (handle both field names for compatibility)
    position_type = position.get('type') or position.get('combo_type')
    
    if position_type == 'butterfly':
        center = position.get('center_strike', 0)
        width = position.get('wing_width', 0)
        
        if center and width:
            distance = abs(spot - center)
            if distance > (width * 0.75):
                exit_signals.append({
                    'trigger': 'POSITION_DRIFT',
                    'reason': f'Spot {spot:.2f} > 75% from center {center:.2f}'
                })
                
            # Check if predicted range excludes the center
            if predicted_range and len(predicted_range) >= 2:
                if not (predicted_range[0] <= center <= predicted_range[1]):
                    exit_signals.append({
                        'trigger': 'RANGE_SHIFT',
                        'reason': f'Predicted range {predicted_range} excludes center {center:.2f}'
                    })
                    
    elif position_type == 'iron_condor':
        sp = position.get('short_put_strike', 0)
        sc = position.get('short_call_strike', 0)
        
        if sp and sc:
            # Check if spot is approaching short strikes (2% buffer)
            if spot <= sp * 1.02:
                exit_signals.append({
                    'trigger': 'POSITION_DRIFT',
                    'reason': f'Spot {spot:.2f} approaching short put {sp:.2f}'
                })
            elif spot >= sc * 0.98:
                exit_signals.append({
                    'trigger': 'POSITION_DRIFT',
                    'reason': f'Spot {spot:.2f} approaching short call {sc:.2f}'
                })
                
    elif position_type == 'vertical':
        direction = position.get('direction')
        trend = magic8_data.get('trend', '').lower()
        
        if direction and trend:
            # Check for trend reversal
            if (direction == 'bull' and trend == 'down') or \
               (direction == 'bear' and trend == 'up'):
                exit_signals.append({
                    'trigger': 'TREND_REVERSAL',
                    'reason': f'Position direction {direction} conflicts with trend {trend}'
                })
        
        # Additional check for vertical spreads moving against position
        lower_strike = position.get('lower_strike', 0)
        upper_strike = position.get('upper_strike', 0)
        option_type = position.get('option_type', '')
        
        if lower_strike and upper_strike:
            if direction == 'bull' and option_type == 'call':
                # Bull call spread - exit if spot falls below lower strike
                if spot < lower_strike * 0.98:
                    exit_signals.append({
                        'trigger': 'POSITION_DRIFT',
                        'reason': f'Spot {spot:.2f} below bull call spread lower strike {lower_strike:.2f}'
                    })
            elif direction == 'bear' and option_type == 'put':
                # Bear put spread - exit if spot rises above upper strike
                if spot > upper_strike * 1.02:
                    exit_signals.append({
                        'trigger': 'POSITION_DRIFT',
                        'reason': f'Spot {spot:.2f} above bear put spread upper strike {upper_strike:.2f}'
                    })
    
    # Universal loss limit check
    unrealized_pnl = position.get('unrealized_pnl') or position.get('current_pnl', 0)
    if unrealized_pnl <= -2000:
        exit_signals.append({
            'trigger': 'LOSS_LIMIT',
            'reason': f"Loss ${abs(unrealized_pnl):.2f} exceeds $2000 limit"
        })
    
    # Time-based exit for 0DTE positions (optional enhancement)
    # Could add logic to exit positions close to expiration
    
    return exit_signals


def format_exit_alert(position: Dict, signals: List[Dict]) -> str:
    """
    Format exit signals into a Discord alert message.
    
    Args:
        position: Position dictionary
        signals: List of exit signals
        
    Returns:
        Formatted alert message
    """
    position_type = position.get('type') or position.get('combo_type', 'Unknown')
    symbol = position.get('symbol', 'SPX')
    strikes_info = position.get('strikes_info', 'N/A')
    pnl = position.get('unrealized_pnl') or position.get('current_pnl', 0)
    
    # Build alert message
    lines = [
        f"🚨 **EXIT SIGNALS** - {position_type.upper()} Position",
        f"Symbol: {symbol}",
        f"Strikes: {strikes_info}",
        f"Current P&L: ${pnl:,.2f}",
        "",
        "**Exit Triggers:**"
    ]
    
    for signal in signals:
        lines.append(f"• {signal['trigger']}: {signal['reason']}")
    
    lines.append("")
    lines.append("**ACTION REQUIRED: Review position for immediate exit**")
    
    return "\n".join(lines)


# Test the enhanced position monitor
if __name__ == '__main__':
    # Test with DB format position
    test_db_position = {
        'id': 1,
        'combo_type': 'butterfly',
        'strikes_info': 'C5000/C5010/C5020',
        'current_pnl': -1500,
        'symbol': 'SPX',
        'direction': 'neutral'
    }
    
    test_magic8_data = {
        'spot_price': 5025,  # Moved away from center
        'trend': 'Up',
        'targets': [5020, 5030],
        'strength': 0.7
    }
    
    signals = check_exit_signals(test_db_position, test_magic8_data)
    print(f"Exit signals: {signals}")
    
    if signals:
        alert = format_exit_alert(test_db_position, signals)
        print(f"\nFormatted alert:\n{alert}")
