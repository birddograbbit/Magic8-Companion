"""
Greeks Wrapper Module
Simple wrapper around py_vollib_vectorized for fast Greeks calculations.
Ship-fast approach: Minimal complexity, maximum reliability.
"""

import numpy as np
from typing import Dict, Union, Optional
import logging
from functools import lru_cache

try:
    from py_vollib_vectorized import get_all_greeks
    VECTORIZED_AVAILABLE = True
except ImportError:
    import py_vollib.black_scholes.greeks.analytical as vol_fallback
    VECTORIZED_AVAILABLE = False
    logging.warning("py_vollib_vectorized not available, using standard py_vollib")

logger = logging.getLogger(__name__)


class GreeksWrapper:
    """
    Wrapper for Greeks calculations using production-ready py_vollib libraries.
    Automatically falls back to standard py_vollib if vectorized version unavailable.
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize Greeks calculator.
        
        Args:
            risk_free_rate: Risk-free interest rate (default 5%)
        """
        self.risk_free_rate = risk_free_rate
        self.use_vectorized = VECTORIZED_AVAILABLE
        
    def calculate_all(
        self,
        spot: float,
        strikes: Union[float, np.ndarray, list],
        time_to_exp: float,
        iv: Union[float, np.ndarray, list],
        option_type: str = 'c'
    ) -> Dict[str, np.ndarray]:
        """
        Calculate all Greeks for given options.
        
        Args:
            spot: Current spot price
            strikes: Strike price(s) - can be single value or array
            time_to_exp: Time to expiration in years (e.g., 1/365 for 1 day)
            iv: Implied volatility (0.20 for 20%)
            option_type: 'c' for call, 'p' for put
            
        Returns:
            Dictionary with keys: delta, gamma, theta, vega, rho
        """
        # Convert inputs to numpy arrays
        strikes = np.atleast_1d(strikes)
        iv = np.atleast_1d(iv)
        
        # Ensure iv is broadcast to match strikes if single value provided
        if iv.shape[0] == 1 and strikes.shape[0] > 1:
            iv = np.full_like(strikes, iv[0])
            
        try:
            if self.use_vectorized:
                return self._calculate_vectorized(spot, strikes, time_to_exp, iv, option_type)
            else:
                return self._calculate_standard(spot, strikes, time_to_exp, iv, option_type)
        except Exception as e:
            logger.error(f"Error calculating Greeks: {e}")
            # Return zero Greeks on error
            return {
                'delta': np.zeros_like(strikes),
                'gamma': np.zeros_like(strikes),
                'theta': np.zeros_like(strikes),
                'vega': np.zeros_like(strikes),
                'rho': np.zeros_like(strikes)
            }
    
    def _calculate_vectorized(
        self,
        spot: float,
        strikes: np.ndarray,
        time_to_exp: float,
        iv: np.ndarray,
        option_type: str
    ) -> Dict[str, np.ndarray]:
        """Calculate Greeks using vectorized library (fast)."""
        # py_vollib_vectorized expects 'flag' parameter as 'c' or 'p'
        # S: spot price
        # K: strikes  
        # t: time to expiration
        # r: risk-free rate
        # sigma: implied volatility
        greeks = get_all_greeks(
            flag=option_type,
            S=spot,
            K=strikes,
            t=time_to_exp,
            r=self.risk_free_rate,
            sigma=iv,
            model='black_scholes',
            return_as='dict'
        )
        
        # Ensure all values are numpy arrays
        for key in greeks:
            greeks[key] = np.atleast_1d(greeks[key])
            
        return greeks
    
    def _calculate_standard(
        self,
        spot: float,
        strikes: np.ndarray,
        time_to_exp: float,
        iv: np.ndarray,
        option_type: str
    ) -> Dict[str, np.ndarray]:
        """Calculate Greeks using standard library (fallback)."""
        # Standard py_vollib works on scalars, so we vectorize manually
        greeks = {
            'delta': np.zeros_like(strikes),
            'gamma': np.zeros_like(strikes),
            'theta': np.zeros_like(strikes),
            'vega': np.zeros_like(strikes),
            'rho': np.zeros_like(strikes)
        }
        
        for i, (strike, vol) in enumerate(zip(strikes, iv)):
            greeks['delta'][i] = vol_fallback.delta(
                option_type, spot, strike, time_to_exp, self.risk_free_rate, vol
            )
            greeks['gamma'][i] = vol_fallback.gamma(
                option_type, spot, strike, time_to_exp, self.risk_free_rate, vol
            )
            greeks['theta'][i] = vol_fallback.theta(
                option_type, spot, strike, time_to_exp, self.risk_free_rate, vol
            )
            greeks['vega'][i] = vol_fallback.vega(
                option_type, spot, strike, time_to_exp, self.risk_free_rate, vol
            )
            greeks['rho'][i] = vol_fallback.rho(
                option_type, spot, strike, time_to_exp, self.risk_free_rate, vol
            )
        
        return greeks
    
    @lru_cache(maxsize=128)
    def calculate_single_cached(
        self,
        spot: float,
        strike: float,
        time_to_exp: float,
        iv: float,
        option_type: str = 'c'
    ) -> Dict[str, float]:
        """
        Cached calculation for single option (useful for repeated calls).
        
        Returns dictionary with scalar values instead of arrays.
        """
        greeks = self.calculate_all(spot, strike, time_to_exp, iv, option_type)
        return {k: float(v[0]) for k, v in greeks.items()}
    
    def delta_neutral_strike(
        self,
        spot: float,
        strikes: np.ndarray,
        time_to_exp: float,
        iv: np.ndarray
    ) -> float:
        """
        Find the strike closest to delta-neutral (delta ≈ 0.5 for calls).
        
        Useful for finding ATM strikes in skewed markets.
        """
        deltas = self.calculate_all(spot, strikes, time_to_exp, iv, 'c')['delta']
        idx = np.argmin(np.abs(deltas - 0.5))
        return float(strikes[idx])
    
    def get_strategy_greeks_adjustments(
        self,
        strategy_type: str,
        greeks: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate scoring adjustments based on Greeks for different strategies.
        
        Ship-fast implementation: Simple rules-based adjustments.
        """
        adjustments = {
            'delta_adjustment': 0.0,
            'theta_adjustment': 0.0,
            'vega_adjustment': 0.0,
            'gamma_adjustment': 0.0
        }
        
        if strategy_type == "Butterfly":
            # Butterflies benefit from theta decay
            if greeks['theta'] < -0.05:  # Negative theta is good
                adjustments['theta_adjustment'] = 5.0
            # Low gamma preferred (stable P&L)
            if abs(greeks['gamma']) < 0.01:
                adjustments['gamma_adjustment'] = 3.0
                
        elif strategy_type == "Iron_Condor":
            # Iron Condors need balanced Greeks
            # Prefer low delta (market neutral)
            if abs(greeks['delta']) < 0.1:
                adjustments['delta_adjustment'] = 4.0
            # Moderate vega exposure OK
            if 0.1 < abs(greeks['vega']) < 0.5:
                adjustments['vega_adjustment'] = 2.0
                
        elif strategy_type == "Vertical":
            # Verticals can handle directional exposure
            # Higher delta OK for directional trades
            if abs(greeks['delta']) > 0.3:
                adjustments['delta_adjustment'] = 3.0
            # Lower gamma preferred
            if abs(greeks['gamma']) < 0.02:
                adjustments['gamma_adjustment'] = 2.0
        
        return adjustments


# Example usage and testing
if __name__ == "__main__":
    # Test the wrapper
    wrapper = GreeksWrapper()
    
    # Test data
    spot = 5850
    strikes = np.array([5800, 5825, 5850, 5875, 5900])
    time_to_exp = 1/365  # 0DTE
    iv = 0.15  # 15% IV
    
    # Calculate all Greeks
    greeks = wrapper.calculate_all(spot, strikes, time_to_exp, iv)
    
    print("Greeks Calculation Test:")
    print(f"Spot: {spot}")
    print(f"Strikes: {strikes}")
    print(f"Time to expiration: {time_to_exp:.4f} years")
    print(f"IV: {iv:.1%}")
    print("\nResults:")
    for greek, values in greeks.items():
        print(f"{greek.capitalize()}: {values}")
    
    # Test delta-neutral strike
    dn_strike = wrapper.delta_neutral_strike(spot, strikes, time_to_exp, iv)
    print(f"\nDelta-neutral strike: {dn_strike}")
    
    # Test strategy adjustments
    sample_greeks = {'delta': 0.5, 'gamma': 0.01, 'theta': -0.1, 'vega': 0.2}
    for strategy in ["Butterfly", "Iron_Condor", "Vertical"]:
        adj = wrapper.get_strategy_greeks_adjustments(strategy, sample_greeks)
        print(f"\n{strategy} adjustments: {adj}")
