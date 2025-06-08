"""
Position Parser Utility

Parses strikes_info strings and maps database positions to the format
expected by position_monitor.py
"""
import re
from typing import Dict, List, Optional, Tuple


def parse_strikes_info(strikes_info: str, combo_type: str) -> Dict[str, float]:
    """
    Parse strikes_info string into individual strike components.
    
    Examples:
    - Butterfly: "C5000/C5010/C5020" -> {center_strike: 5010, wing_width: 10}
    - Iron Condor: "P4900/P4905_C5100/C5105" -> {short_put: 4905, short_call: 5100, ...}
    - Vertical: "C5000/C5010" -> {lower_strike: 5000, upper_strike: 5010}
    
    Args:
        strikes_info: String representation of strikes
        combo_type: Type of combo ('butterfly', 'iron_condor', 'vertical')
        
    Returns:
        Dictionary with parsed strike values
    """
    parsed = {}
    
    try:
        if combo_type == 'butterfly':
            # Format: "C5000/C5010/C5020" or "P5000/P5010/P5020"
            matches = re.findall(r'[CP](\d+(?:\.\d+)?)', strikes_info)
            if len(matches) == 3:
                strikes = sorted([float(s) for s in matches])
                parsed['center_strike'] = strikes[1]
                parsed['wing_width'] = strikes[1] - strikes[0]
                parsed['lower_wing'] = strikes[0]
                parsed['upper_wing'] = strikes[2]
                
        elif combo_type == 'iron_condor':
            # Format: "P4900/P4905_C5100/C5105"
            parts = strikes_info.split('_')
            if len(parts) == 2:
                # Parse put side
                put_matches = re.findall(r'P(\d+(?:\.\d+)?)', parts[0])
                if len(put_matches) >= 2:
                    put_strikes = sorted([float(s) for s in put_matches])
                    parsed['long_put_strike'] = put_strikes[0]
                    parsed['short_put_strike'] = put_strikes[1]
                
                # Parse call side
                call_matches = re.findall(r'C(\d+(?:\.\d+)?)', parts[1])
                if len(call_matches) >= 2:
                    call_strikes = sorted([float(s) for s in call_matches])
                    parsed['short_call_strike'] = call_strikes[0]
                    parsed['long_call_strike'] = call_strikes[1]
                    
        elif combo_type == 'vertical':
            # Format: "C5000/C5010" or "P5000/P5010"
            option_type = 'call' if 'C' in strikes_info else 'put'
            matches = re.findall(r'[CP](\d+(?:\.\d+)?)', strikes_info)
            if len(matches) == 2:
                strikes = sorted([float(s) for s in matches])
                parsed['lower_strike'] = strikes[0]
                parsed['upper_strike'] = strikes[1]
                parsed['option_type'] = option_type
                # Determine direction based on typical vertical spread construction
                # For calls: buy lower, sell higher = bull
                # For puts: buy higher, sell lower = bull
                parsed['spread_width'] = strikes[1] - strikes[0]
                
    except (ValueError, IndexError) as e:
        print(f"Error parsing strikes_info '{strikes_info}' for {combo_type}: {e}")
        
    return parsed


def parse_direction_from_strikes(strikes_info: str, combo_type: str) -> Optional[str]:
    """
    Infer direction from strikes_info for vertical spreads.
    
    Returns:
        'bull', 'bear', or 'neutral'
    """
    if combo_type != 'vertical':
        return 'neutral'
        
    # Check if it's a debit or credit spread based on the order
    # This is a simplified heuristic - in reality, we'd need the trade direction
    if 'C' in strikes_info:
        # Call spread - if bought lower strike, it's bullish
        return 'bull'
    elif 'P' in strikes_info:
        # Put spread - if bought higher strike, it's bullish
        return 'bear'
    
    return None


def map_db_position_to_monitor_format(db_position: Dict) -> Dict:
    """
    Convert database position format to position_monitor expected format.
    
    Maps 'combo_type' to 'type' and parses strikes_info into individual fields.
    
    Args:
        db_position: Position dict from database
        
    Returns:
        Position dict in format expected by position_monitor
    """
    # Start with a copy of the original
    monitor_position = db_position.copy()
    
    # Map combo_type to type
    monitor_position['type'] = db_position.get('combo_type', '')
    
    # Parse strikes info
    strikes_info = db_position.get('strikes_info', '')
    combo_type = db_position.get('combo_type', '')
    
    if strikes_info and combo_type:
        parsed_strikes = parse_strikes_info(strikes_info, combo_type)
        monitor_position.update(parsed_strikes)
    
    # Handle direction
    if 'direction' not in monitor_position or not monitor_position['direction']:
        direction = parse_direction_from_strikes(strikes_info, combo_type)
        if direction:
            monitor_position['direction'] = direction
    
    # Ensure unrealized_pnl exists (map from current_pnl)
    if 'unrealized_pnl' not in monitor_position:
        monitor_position['unrealized_pnl'] = db_position.get('current_pnl', 0)
    
    return monitor_position


def format_strikes_for_db(combo_type: str, strikes: Dict) -> str:
    """
    Format strike prices into strikes_info string for database storage.
    
    Args:
        combo_type: Type of combo
        strikes: Dictionary with strike information
        
    Returns:
        Formatted strikes_info string
    """
    if combo_type == 'butterfly':
        # Expects: lower_wing, center_strike, upper_wing
        lower = strikes.get('lower_wing', 0)
        center = strikes.get('center_strike', 0)
        upper = strikes.get('upper_wing', 0)
        option_type = strikes.get('option_type', 'C')
        return f"{option_type}{lower}/{option_type}{center}/{option_type}{upper}"
        
    elif combo_type == 'iron_condor':
        # Expects: long_put, short_put, short_call, long_call
        lp = strikes.get('long_put_strike', 0)
        sp = strikes.get('short_put_strike', 0)
        sc = strikes.get('short_call_strike', 0)
        lc = strikes.get('long_call_strike', 0)
        return f"P{lp}/P{sp}_C{sc}/C{lc}"
        
    elif combo_type == 'vertical':
        # Expects: lower_strike, upper_strike, option_type
        lower = strikes.get('lower_strike', 0)
        upper = strikes.get('upper_strike', 0)
        option_type = strikes.get('option_type', 'C')
        prefix = 'C' if option_type == 'call' else 'P'
        return f"{prefix}{lower}/{prefix}{upper}"
        
    return ""


# Test the parser
if __name__ == '__main__':
    # Test butterfly parsing
    bf_strikes = "C5000/C5010/C5020"
    bf_parsed = parse_strikes_info(bf_strikes, 'butterfly')
    print(f"Butterfly: {bf_strikes} -> {bf_parsed}")
    
    # Test iron condor parsing
    ic_strikes = "P4900/P4905_C5100/C5105"
    ic_parsed = parse_strikes_info(ic_strikes, 'iron_condor')
    print(f"Iron Condor: {ic_strikes} -> {ic_parsed}")
    
    # Test vertical parsing
    v_strikes = "C5000/C5010"
    v_parsed = parse_strikes_info(v_strikes, 'vertical')
    print(f"Vertical: {v_strikes} -> {v_parsed}")
    
    # Test full position mapping
    test_position = {
        'id': 1,
        'combo_type': 'butterfly',
        'strikes_info': 'C5000/C5010/C5020',
        'current_pnl': -500,
        'symbol': 'SPX'
    }
    mapped = map_db_position_to_monitor_format(test_position)
    print(f"\nMapped position: {mapped}")
