"""
Gamma Levels Analyzer for Magic8-Companion.
Identifies key support/resistance levels from GEX distribution.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GammaLevels:
    """Identify key support/resistance levels from GEX."""
    
    @staticmethod
    def find_levels(strike_gex: Dict[float, Dict], 
                   spot_price: float,
                   min_gex_threshold: float = 1e6) -> Dict:
        """
        Find call wall, put wall, and zero gamma levels.
        
        Args:
            strike_gex: Dict of strike -> GEX data
            spot_price: Current spot price
            min_gex_threshold: Minimum GEX to consider for walls
            
        Returns:
            Dict with identified levels
        """
        if not strike_gex:
            return GammaLevels._empty_levels()
        
        # Find walls (highest absolute GEX)
        call_wall = GammaLevels._find_call_wall(strike_gex, spot_price, min_gex_threshold)
        put_wall = GammaLevels._find_put_wall(strike_gex, spot_price, min_gex_threshold)
        
        # Find zero gamma level
        zero_gamma = GammaLevels._find_zero_gamma(strike_gex)
        
        # Find high gamma strikes
        high_gamma_strikes = GammaLevels._find_high_gamma_strikes(strike_gex, 5)
        
        # Calculate gamma profile
        gamma_profile = GammaLevels._calculate_gamma_profile(strike_gex, spot_price)
        
        # Find flip zone
        flip_zone = GammaLevels._find_flip_zone(strike_gex, spot_price)
        
        return {
            'call_wall': call_wall,
            'put_wall': put_wall,
            'zero_gamma': zero_gamma,
            'high_gamma_strikes': high_gamma_strikes,
            'gamma_profile': gamma_profile,
            'flip_zone': flip_zone,
            'levels_strength': GammaLevels._calculate_levels_strength(
                call_wall, put_wall, strike_gex
            )
        }
    
    @staticmethod
    def _find_call_wall(strike_gex: Dict, spot_price: float, 
                       min_threshold: float) -> Optional[float]:
        """Find the call wall (highest call GEX above spot)."""
        call_strikes = {
            k: v for k, v in strike_gex.items()
            if k > spot_price and abs(v['call_gex']) >= min_threshold
        }
        
        if not call_strikes:
            return None
        
        # Find strike with highest absolute call GEX
        call_wall = max(call_strikes.items(), 
                       key=lambda x: abs(x[1]['call_gex']))[0]
        
        return call_wall
    
    @staticmethod
    def _find_put_wall(strike_gex: Dict, spot_price: float,
                      min_threshold: float) -> Optional[float]:
        """Find the put wall (highest put GEX below spot)."""
        put_strikes = {
            k: v for k, v in strike_gex.items()
            if k < spot_price and abs(v['put_gex']) >= min_threshold
        }
        
        if not put_strikes:
            return None
        
        # Find strike with highest absolute put GEX
        put_wall = max(put_strikes.items(),
                      key=lambda x: abs(x[1]['put_gex']))[0]
        
        return put_wall
    
    @staticmethod
    def _find_zero_gamma(strike_gex: Dict) -> Optional[float]:
        """Find where net GEX crosses zero."""
        if not strike_gex:
            return None
        
        strikes = sorted(strike_gex.keys())
        
        for i in range(len(strikes) - 1):
            curr_gex = strike_gex[strikes[i]]['net_gex']
            next_gex = strike_gex[strikes[i + 1]]['net_gex']
            
            # Check for sign change
            if curr_gex * next_gex < 0:
                # Interpolate zero crossing
                curr_strike = strikes[i]
                next_strike = strikes[i + 1]
                
                # Linear interpolation
                zero_gamma = curr_strike + (
                    (0 - curr_gex) / (next_gex - curr_gex) * 
                    (next_strike - curr_strike)
                )
                
                return zero_gamma
        
        return None
    
    @staticmethod
    def _find_high_gamma_strikes(strike_gex: Dict, top_n: int = 5) -> List[Dict]:
        """Find strikes with highest absolute GEX."""
        if not strike_gex:
            return []
        
        # Sort by absolute net GEX
        sorted_strikes = sorted(
            strike_gex.items(),
            key=lambda x: abs(x[1]['net_gex']),
            reverse=True
        )
        
        high_gamma_strikes = []
        for strike, data in sorted_strikes[:top_n]:
            high_gamma_strikes.append({
                'strike': strike,
                'net_gex': data['net_gex'],
                'call_gex': data['call_gex'],
                'put_gex': data['put_gex'],
                'dominant_side': 'call' if abs(data['call_gex']) > abs(data['put_gex']) else 'put'
            })
        
        return high_gamma_strikes
    
    @staticmethod
    def _calculate_gamma_profile(strike_gex: Dict, spot_price: float) -> Dict:
        """Calculate the gamma profile around spot."""
        if not strike_gex:
            return {'skew': 0.0, 'concentration': 0.0}
        
        # Calculate GEX-weighted average strike
        total_abs_gex = sum(abs(v['net_gex']) for v in strike_gex.values())
        if total_abs_gex == 0:
            return {'skew': 0.0, 'concentration': 0.0}
        
        weighted_strike = sum(
            k * abs(v['net_gex']) for k, v in strike_gex.items()
        ) / total_abs_gex
        
        # Calculate skew (positive = call-heavy, negative = put-heavy)
        skew = (weighted_strike - spot_price) / spot_price
        
        # Calculate concentration around spot (within 5%)
        near_spot_range = 0.05
        near_spot_gex = sum(
            abs(v['net_gex']) for k, v in strike_gex.items()
            if abs(k - spot_price) / spot_price <= near_spot_range
        )
        
        concentration = near_spot_gex / total_abs_gex if total_abs_gex > 0 else 0
        
        return {
            'skew': skew,
            'concentration': concentration,
            'weighted_strike': weighted_strike
        }
    
    @staticmethod
    def _find_flip_zone(strike_gex: Dict, spot_price: float) -> Dict:
        """Find the gamma flip zone (where dealers flip from long to short gamma)."""
        if not strike_gex:
            return {'lower': None, 'upper': None, 'width': 0}
        
        # Find strikes where net GEX is close to zero (within 20% of max abs GEX)
        max_abs_gex = max(abs(v['net_gex']) for v in strike_gex.values())
        if max_abs_gex == 0:
            return {'lower': None, 'upper': None, 'width': 0}
        
        flip_threshold = max_abs_gex * 0.2
        
        flip_strikes = [
            k for k, v in strike_gex.items()
            if abs(v['net_gex']) <= flip_threshold
        ]
        
        if not flip_strikes:
            return {'lower': None, 'upper': None, 'width': 0}
        
        # Find the flip zone boundaries
        lower = min(flip_strikes)
        upper = max(flip_strikes)
        
        return {
            'lower': lower,
            'upper': upper,
            'width': upper - lower,
            'spot_in_zone': lower <= spot_price <= upper
        }
    
    @staticmethod
    def _calculate_levels_strength(call_wall: Optional[float],
                                 put_wall: Optional[float],
                                 strike_gex: Dict) -> Dict:
        """Calculate the strength of identified levels."""
        strength = {
            'call_wall_strength': 0.0,
            'put_wall_strength': 0.0,
            'range_width': 0.0
        }
        
        if not strike_gex:
            return strength
        
        max_abs_gex = max(abs(v['net_gex']) for v in strike_gex.values())
        if max_abs_gex == 0:
            return strength
        
        # Calculate wall strengths as percentage of max GEX
        if call_wall and call_wall in strike_gex:
            call_wall_gex = abs(strike_gex[call_wall]['call_gex'])
            strength['call_wall_strength'] = call_wall_gex / max_abs_gex
        
        if put_wall and put_wall in strike_gex:
            put_wall_gex = abs(strike_gex[put_wall]['put_gex'])
            strength['put_wall_strength'] = put_wall_gex / max_abs_gex
        
        # Calculate range width
        if call_wall and put_wall:
            strength['range_width'] = call_wall - put_wall
        
        return strength
    
    @staticmethod
    def _empty_levels() -> Dict:
        """Return empty levels structure."""
        return {
            'call_wall': None,
            'put_wall': None,
            'zero_gamma': None,
            'high_gamma_strikes': [],
            'gamma_profile': {'skew': 0.0, 'concentration': 0.0},
            'flip_zone': {'lower': None, 'upper': None, 'width': 0},
            'levels_strength': {
                'call_wall_strength': 0.0,
                'put_wall_strength': 0.0,
                'range_width': 0.0
            }
        }
