"""
Gamma Exposure Analysis Module
Based on the expansion plan's gamma calculations
Migrated from MLOptionTrading for integrated gamma analysis in Magic8-Companion
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.stats import norm
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GammaExposureAnalyzer:
    """
    Calculate dealer gamma exposure and identify key levels
    Based on: https://github.com/jensolson/SPX-Gamma-Exposure concepts
    """

    def __init__(self, spot_multiplier: int = 100, zero_dte_multiplier: int = 8):
        """
        Initialize gamma analyzer
        
        Args:
            spot_multiplier: Contract multiplier (100 for SPX)
            zero_dte_multiplier: Multiplier for 0DTE gamma (typically 8x)
        """
        self.spot_multiplier = spot_multiplier
        self.zero_dte_multiplier = zero_dte_multiplier
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def calculate_gamma(self, S: float, K: float, T: float,
                       r: float, sigma: float, option_type: str = 'call') -> float:
        """
        Black-Scholes gamma calculation
        
        Args:
            S: Spot price
            K: Strike price
            T: Time to expiry (years)
            r: Risk-free rate
            sigma: Implied volatility
            option_type: 'call' or 'put' (gamma is same for both)
            
        Returns:
            Gamma value
        """
        if T <= 0:
            return 0.0
            
        try:
            d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))
            gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
            return gamma
        except Exception as e:
            self.logger.error(f"Error calculating gamma: {e}")
            return 0.0

    def calculate_gex(self, option_chain: pd.DataFrame,
                     spot_price: float) -> Dict:
        """
        Calculate net gamma exposure and key levels
        
        Args:
            option_chain: DataFrame with columns:
                - strike: Strike price
                - dte: Days to expiry
                - call_oi: Call open interest
                - put_oi: Put open interest
                - call_iv: Call implied volatility
                - put_iv: Put implied volatility
            spot_price: Current spot price
            
        Returns:
            Dictionary with GEX metrics and key levels
        """
        results = {
            'net_gex': 0,
            'call_gex': 0,
            'put_gex': 0,
            'strike_gex': {},
            'timestamp': datetime.now().isoformat()
        }

        # Risk-free rate (simplified - could be passed in)
        r = 0.05

        for _, opt in option_chain.iterrows():
            strike = opt['strike']
            dte = opt['dte']

            # Use small time value for 0DTE so multiplier can be applied
            if dte == 0:
                T = 0.25 / 365.0  # assume quarter day remaining
            else:
                T = dte / 365.0

            # Calculate gamma for calls and puts
            call_gamma = self.calculate_gamma(
                spot_price, strike, T, r, opt['call_iv'], 'call'
            )
            put_gamma = self.calculate_gamma(
                spot_price, strike, T, r, opt['put_iv'], 'put'
            )

            # Apply 0DTE multiplier if applicable
            if dte < 1:
                call_gamma *= self.zero_dte_multiplier
                put_gamma *= self.zero_dte_multiplier

            # Calculate GEX (dealers short calls, long puts)
            # Negative for calls because dealers are typically short
            call_gex = -call_gamma * opt['call_oi'] * self.spot_multiplier * spot_price
            put_gex = put_gamma * opt['put_oi'] * self.spot_multiplier * spot_price

            results['call_gex'] += call_gex
            results['put_gex'] += put_gex
            results['strike_gex'][strike] = call_gex + put_gex

        results['net_gex'] = results['call_gex'] + results['put_gex']

        # Find key levels
        key_levels = self._find_key_levels(results['strike_gex'], spot_price)
        results.update(key_levels)

        return results

    def _find_key_levels(self, strike_gex: Dict[float, float], 
                        spot: float) -> Dict:
        """
        Identify gamma walls and flip point
        
        Args:
            strike_gex: Dictionary of strike -> GEX
            spot: Current spot price
            
        Returns:
            Dictionary with key levels
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

        # Sort by strike for cumulative sum
        df = df.sort_values('strike')
        df['cumsum_gex'] = df['gex'].cumsum()

        # Gamma flip point (where cumulative GEX crosses zero)
        if len(df[df['cumsum_gex'] >= 0]) > 0 and len(df[df['cumsum_gex'] < 0]) > 0:
            # Find the strike where cumsum crosses zero
            flip_idx = df['cumsum_gex'].abs().idxmin()
            gamma_flip = df.loc[flip_idx, 'strike']
        else:
            gamma_flip = spot

        # Call wall (highest positive gamma above spot)
        call_df = df[df['strike'] > spot]
        if len(call_df) > 0 and len(call_df[call_df['gex'] > 0]) > 0:
            call_wall = call_df.loc[call_df['gex'].idxmax(), 'strike']
        else:
            call_wall = spot + 50

        # Put wall (highest negative gamma below spot)  
        put_df = df[df['strike'] < spot]
        if len(put_df) > 0 and len(put_df[put_df['gex'] < 0]) > 0:
            put_wall = put_df.loc[put_df['gex'].idxmin(), 'strike']
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

    def get_gamma_signals(self, gex_data: Dict, spot: float) -> Dict:
        """
        Convert gamma data to trading signals
        
        Args:
            gex_data: Output from calculate_gex
            spot: Current spot price
            
        Returns:
            Dictionary with trading signals
        """
        signals = {
            'gamma_regime': 'positive' if gex_data['net_gex'] > 0 else 'negative',
            'volatility_expectation': 'dampened' if gex_data['net_gex'] > 0 else 'amplified',
            'support_level': gex_data['put_wall'],
            'resistance_level': gex_data['call_wall'],
            'key_level': gex_data['gamma_flip']
        }

        # Distance to walls (as %)
        if spot != 0:
            signals['distance_to_call_wall'] = (gex_data['call_wall'] - spot) / spot
            signals['distance_to_put_wall'] = (spot - gex_data['put_wall']) / spot
        else:
            signals['distance_to_call_wall'] = 0
            signals['distance_to_put_wall'] = 0

        # Trading bias based on position relative to gamma flip
        if spot > gex_data['gamma_flip']:
            if signals['distance_to_call_wall'] < 0.003:  # Within 0.3% of call wall
                signals['bias'] = 'fade_rallies'
                signals['signal_strength'] = 'strong'
            else:
                signals['bias'] = 'neutral_positive'
                signals['signal_strength'] = 'moderate'
        else:
            if signals['distance_to_put_wall'] < 0.003:  # Within 0.3% of put wall
                signals['bias'] = 'buy_dips'
                signals['signal_strength'] = 'strong'
            else:
                signals['bias'] = 'neutral_negative'
                signals['signal_strength'] = 'moderate'

        # Add confidence based on GEX magnitude
        abs_gex = abs(gex_data['net_gex'])
        if abs_gex > 1e9:  # High GEX (in billions)
            signals['confidence'] = 'high'
        elif abs_gex > 5e8:  # Medium GEX
            signals['confidence'] = 'medium'
        else:
            signals['confidence'] = 'low'

        return signals


def create_sample_option_chain() -> pd.DataFrame:
    """
    Create a sample option chain for testing
    """
    strikes = list(range(5800, 6201, 25))
    spot = 6000
    
    data = []
    for strike in strikes:
        # Simulate realistic OI distribution (higher near ATM)
        distance_from_atm = abs(strike - spot) / spot
        base_oi = 10000 * np.exp(-distance_from_atm * 10)
        
        # Add some randomness
        call_oi = int(base_oi * (1 + np.random.uniform(-0.3, 0.3)))
        put_oi = int(base_oi * (1 + np.random.uniform(-0.3, 0.3)))
        
        # IV smile
        base_iv = 0.15
        iv_adjustment = distance_from_atm * 0.5
        call_iv = base_iv + iv_adjustment + np.random.uniform(-0.01, 0.01)
        put_iv = base_iv + iv_adjustment + np.random.uniform(-0.01, 0.01)
        
        data.append({
            'strike': strike,
            'dte': 0,  # 0DTE
            'call_oi': call_oi,
            'put_oi': put_oi,
            'call_iv': call_iv,
            'put_iv': put_iv
        })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Example usage - demonstration purposes only.
    # Do NOT execute in production environments.
    analyzer = GammaExposureAnalyzer()
    
    # Create sample data
    option_chain = create_sample_option_chain()
    spot_price = 6000
    
    # Calculate GEX
    gex_data = analyzer.calculate_gex(option_chain, spot_price)
    
    # Get trading signals
    signals = analyzer.get_gamma_signals(gex_data, spot_price)
    
    # Print results
    print(f"Net GEX: ${gex_data['net_gex']:,.0f}")
    print(f"Gamma Flip: {gex_data['gamma_flip']:.0f}")
    print(f"Call Wall: {gex_data['call_wall']:.0f}")
    print(f"Put Wall: {gex_data['put_wall']:.0f}")
    print(f"\nTrading Signals:")
    print(f"Regime: {signals['gamma_regime']}")
    print(f"Bias: {signals['bias']}")
    print(f"Confidence: {signals['confidence']}")
