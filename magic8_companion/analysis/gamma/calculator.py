"""
Gamma Exposure Calculator for Magic8-Companion.
Native implementation of GEX calculations previously in MLOptionTrading.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, time
import json

logger = logging.getLogger(__name__)


class GammaExposureCalculator:
    """Calculate Gamma Exposure (GEX) from option chain data."""
    
    def __init__(self, spot_multiplier: int = 100):
        """
        Initialize GEX calculator.
        
        Args:
            spot_multiplier: Contract multiplier (10 for SPX/RUT, 100 for others)
        """
        self.spot_multiplier = spot_multiplier
        self.call_oi_weight = 1.0  # Weight for call OI
        self.put_oi_weight = 1.0   # Weight for put OI
        
    def calculate_gex(self, 
                     spot_price: float,
                     option_chain: List[Dict],
                     use_0dte_multiplier: bool = True,
                     dte_multiplier: float = 8.0) -> Dict:
        """
        Calculate net GEX from option chain data.
        
        Args:
            spot_price: Current underlying price
            option_chain: List of option data with strikes, OI, gamma
            use_0dte_multiplier: Apply higher weight to 0DTE options
            dte_multiplier: Multiplier for 0DTE options
            
        Returns:
            Dict with net_gex, regime, strike_gex, levels
        """
        if not option_chain:
            logger.warning("Empty option chain provided")
            return self._empty_result()
        
        strike_gex = {}
        total_call_gex = 0
        total_put_gex = 0
        
        for option in option_chain:
            try:
                strike = float(option.get('strike', 0))
                if strike == 0:
                    continue
                
                # Get DTE and apply multiplier if 0DTE
                dte = option.get('dte', 1)
                multiplier = dte_multiplier if (dte == 0 and use_0dte_multiplier) else 1.0
                
                # Call GEX (negative because MM short calls)
                call_gamma = float(option.get('call_gamma', 0))
                call_oi = float(option.get('call_oi', 0))
                call_gex = -1 * (
                    call_gamma * 
                    call_oi * 
                    self.spot_multiplier * 
                    spot_price *
                    self.call_oi_weight *
                    multiplier
                )
                
                # Put GEX (positive because MM short puts)
                put_gamma = float(option.get('put_gamma', 0))
                put_oi = float(option.get('put_oi', 0))
                put_gex = (
                    put_gamma * 
                    put_oi * 
                    self.spot_multiplier * 
                    spot_price *
                    self.put_oi_weight *
                    multiplier
                )
                
                # Store strike-level GEX
                strike_gex[strike] = {
                    'call_gex': call_gex,
                    'put_gex': put_gex,
                    'net_gex': call_gex + put_gex,
                    'call_oi': call_oi,
                    'put_oi': put_oi,
                    'dte': dte
                }
                
                total_call_gex += call_gex
                total_put_gex += put_gex
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing option at strike {option.get('strike')}: {e}")
                continue
        
        net_gex = total_call_gex + total_put_gex
        
        # Calculate additional metrics
        metrics = self._calculate_metrics(strike_gex, spot_price)
        
        return {
            'net_gex': net_gex,
            'total_call_gex': total_call_gex,
            'total_put_gex': total_put_gex,
            'strike_gex': strike_gex,
            'regime': 'positive' if net_gex > 0 else 'negative',
            'spot_price': spot_price,
            'timestamp': datetime.now().isoformat(),
            **metrics
        }
    
    def _calculate_metrics(self, strike_gex: Dict, spot_price: float) -> Dict:
        """Calculate additional GEX metrics."""
        if not strike_gex:
            return {}
        
        # Calculate GEX by strike ranges
        atm_range = 0.02  # 2% ATM range
        atm_strikes = {
            k: v for k, v in strike_gex.items() 
            if abs(k - spot_price) / spot_price <= atm_range
        }
        
        otm_put_strikes = {
            k: v for k, v in strike_gex.items() 
            if k < spot_price * (1 - atm_range)
        }
        
        otm_call_strikes = {
            k: v for k, v in strike_gex.items() 
            if k > spot_price * (1 + atm_range)
        }
        
        # Sum GEX by region
        atm_gex = sum(v['net_gex'] for v in atm_strikes.values())
        otm_put_gex = sum(v['net_gex'] for v in otm_put_strikes.values())
        otm_call_gex = sum(v['net_gex'] for v in otm_call_strikes.values())
        
        # Find largest GEX strikes
        sorted_strikes = sorted(
            strike_gex.items(),
            key=lambda x: abs(x[1]['net_gex']),
            reverse=True
        )
        
        largest_gex_strikes = [
            {
                'strike': k,
                'net_gex': v['net_gex'],
                'type': 'call' if v['call_gex'] > abs(v['put_gex']) else 'put'
            }
            for k, v in sorted_strikes[:5]
        ]
        
        return {
            'atm_gex': atm_gex,
            'otm_put_gex': otm_put_gex,
            'otm_call_gex': otm_call_gex,
            'largest_gex_strikes': largest_gex_strikes,
            'gex_concentration': self._calculate_concentration(strike_gex)
        }
    
    def _calculate_concentration(self, strike_gex: Dict) -> float:
        """Calculate GEX concentration (0-1, higher = more concentrated)."""
        if not strike_gex:
            return 0.0
        
        # Get absolute GEX values
        abs_gex_values = [abs(v['net_gex']) for v in strike_gex.values()]
        total_abs_gex = sum(abs_gex_values)
        
        if total_abs_gex == 0:
            return 0.0
        
        # Calculate Herfindahl index
        herfindahl = sum((gex / total_abs_gex) ** 2 for gex in abs_gex_values)
        
        return herfindahl
    
    def _empty_result(self) -> Dict:
        """Return empty result structure."""
        return {
            'net_gex': 0.0,
            'total_call_gex': 0.0,
            'total_put_gex': 0.0,
            'strike_gex': {},
            'regime': 'neutral',
            'spot_price': 0.0,
            'timestamp': datetime.now().isoformat(),
            'atm_gex': 0.0,
            'otm_put_gex': 0.0,
            'otm_call_gex': 0.0,
            'largest_gex_strikes': [],
            'gex_concentration': 0.0
        }
    
    def calculate_intraday_change(self, 
                                 current_gex: Dict,
                                 previous_gex: Dict) -> Dict:
        """Calculate intraday GEX changes."""
        if not previous_gex:
            return {'change_pct': 0.0, 'regime_changed': False}
        
        prev_net = previous_gex.get('net_gex', 0)
        curr_net = current_gex.get('net_gex', 0)
        
        change_pct = 0.0
        if prev_net != 0:
            change_pct = ((curr_net - prev_net) / abs(prev_net)) * 100
        
        regime_changed = (
            previous_gex.get('regime') != current_gex.get('regime')
        )
        
        return {
            'previous_gex': prev_net,
            'current_gex': curr_net,
            'change_absolute': curr_net - prev_net,
            'change_pct': change_pct,
            'regime_changed': regime_changed,
            'previous_regime': previous_gex.get('regime'),
            'current_regime': current_gex.get('regime')
        }
