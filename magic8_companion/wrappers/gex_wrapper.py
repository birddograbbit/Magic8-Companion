"""
Gamma Exposure (GEX) Wrapper Module
Implements net gamma exposure calculations inspired by production systems.
Ship-fast approach: Essential calculations only, no complex dependencies.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptionData:
    """Simple data class for option chain data."""
    strike: float
    call_gamma: float
    put_gamma: float
    call_oi: float
    put_oi: float
    spot_price: float


class GammaExposureWrapper:
    """
    Wrapper for Gamma Exposure calculations.
    Inspired by jensolson/SPX-Gamma-Exposure methodology.
    
    Key concepts:
    - Net GEX = Call GEX - Put GEX
    - 0DTE options have ~8x gamma sensitivity
    - Gamma walls indicate support/resistance levels
    """
    
    def __init__(self, spot_multiplier: float = 100.0):
        """
        Initialize GEX calculator.
        
        Args:
            spot_multiplier: Contract multiplier (e.g., 100 for SPX)
        """
        self.spot_multiplier = spot_multiplier
        self.ZERO_DTE_GAMMA_MULTIPLIER = 8.0  # Based on market research
        
    def calculate_net_gex(
        self,
        option_chain: List[Dict],
        spot_price: float,
        is_zero_dte: bool = True
    ) -> Dict[str, float]:
        """
        Calculate net gamma exposure from option chain data.
        
        Args:
            option_chain: List of option data dictionaries
            spot_price: Current spot price
            is_zero_dte: Whether these are 0DTE options
            
        Returns:
            Dictionary with GEX metrics
        """
        try:
            # Convert to structured data
            options = self._parse_option_chain(option_chain, spot_price)
            
            # Calculate GEX components
            call_gex = self._calculate_call_gex(options)
            put_gex = self._calculate_put_gex(options)
            net_gex = call_gex - put_gex
            
            # Apply 0DTE multiplier if applicable
            if is_zero_dte:
                net_gex *= self.ZERO_DTE_GAMMA_MULTIPLIER
                call_gex *= self.ZERO_DTE_GAMMA_MULTIPLIER
                put_gex *= self.ZERO_DTE_GAMMA_MULTIPLIER
            
            # Find gamma walls
            gamma_walls = self._find_gamma_walls(options)
            
            # Calculate dealer positioning metric
            dealer_position = self._calculate_dealer_positioning(net_gex, spot_price)
            
            return {
                'net_gex': net_gex,
                'call_gex': call_gex,
                'put_gex': put_gex,
                'gamma_walls': gamma_walls,
                'dealer_position': dealer_position,
                'gex_per_point': net_gex / spot_price if spot_price > 0 else 0,
                'is_zero_dte': is_zero_dte
            }
            
        except Exception as e:
            logger.error(f"Error calculating GEX: {e}")
            return self._empty_gex_result()
    
    def _parse_option_chain(
        self,
        option_chain: List[Dict],
        spot_price: float
    ) -> List[OptionData]:
        """Parse raw option chain into structured format."""
        options = []
        
        for opt in option_chain:
            try:
                # Extract data with safe defaults
                strike = float(opt.get('strike', 0))
                call_gamma = float(opt.get('call_gamma', 0))
                put_gamma = float(opt.get('put_gamma', 0))
                call_oi = float(opt.get('call_open_interest', 0))
                put_oi = float(opt.get('put_open_interest', 0))
                
                if strike > 0:  # Valid strike
                    options.append(OptionData(
                        strike=strike,
                        call_gamma=call_gamma,
                        put_gamma=put_gamma,
                        call_oi=call_oi,
                        put_oi=put_oi,
                        spot_price=spot_price
                    ))
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping invalid option data: {e}")
                continue
                
        return options
    
    def _calculate_call_gex(self, options: List[OptionData]) -> float:
        """
        Calculate total call gamma exposure.
        Call GEX = Spot * Gamma * Open Interest * Contract Multiplier
        """
        total_gex = 0.0
        
        for opt in options:
            # Market makers are short calls (negative gamma)
            gex = -1 * opt.spot_price * opt.call_gamma * opt.call_oi * self.spot_multiplier
            total_gex += gex
            
        return total_gex
    
    def _calculate_put_gex(self, options: List[OptionData]) -> float:
        """
        Calculate total put gamma exposure.
        Put GEX = Spot * Gamma * Open Interest * Contract Multiplier
        """
        total_gex = 0.0
        
        for opt in options:
            # Market makers are long puts (positive gamma)
            gex = opt.spot_price * opt.put_gamma * opt.put_oi * self.spot_multiplier
            total_gex += gex
            
        return total_gex
    
    def _find_gamma_walls(
        self,
        options: List[OptionData],
        top_n: int = 3
    ) -> List[float]:
        """
        Find strikes with highest gamma exposure (potential support/resistance).
        
        Args:
            options: Parsed option data
            top_n: Number of gamma walls to return
            
        Returns:
            List of strike prices representing gamma walls
        """
        strike_gex = {}
        
        for opt in options:
            total_gamma = (opt.call_gamma * opt.call_oi + 
                          opt.put_gamma * opt.put_oi)
            strike_gex[opt.strike] = total_gamma
        
        # Sort by total gamma exposure
        sorted_strikes = sorted(strike_gex.items(), 
                               key=lambda x: x[1], 
                               reverse=True)
        
        # Return top N strikes
        gamma_walls = [strike for strike, _ in sorted_strikes[:top_n]]
        
        return gamma_walls
    
    def _calculate_dealer_positioning(
        self,
        net_gex: float,
        spot_price: float
    ) -> str:
        """
        Interpret dealer positioning based on net GEX.
        
        Positive net GEX: Dealers are long gamma (sell rallies, buy dips)
        Negative net GEX: Dealers are short gamma (buy rallies, sell dips)
        """
        if net_gex > spot_price * 1e8:  # Significantly positive
            return "LONG_GAMMA_STRONG"
        elif net_gex > 0:
            return "LONG_GAMMA"
        elif net_gex > -spot_price * 1e8:  # Slightly negative
            return "SHORT_GAMMA"
        else:
            return "SHORT_GAMMA_STRONG"
    
    def _empty_gex_result(self) -> Dict[str, float]:
        """Return empty GEX result for error cases."""
        return {
            'net_gex': 0.0,
            'call_gex': 0.0,
            'put_gex': 0.0,
            'gamma_walls': [],
            'dealer_position': "NEUTRAL",
            'gex_per_point': 0.0,
            'is_zero_dte': False
        }
    
    def get_strategy_gex_adjustments(
        self,
        strategy_type: str,
        gex_data: Dict[str, float],
        spot_price: float
    ) -> Dict[str, float]:
        """
        Calculate scoring adjustments based on GEX for different strategies.
        
        Ship-fast implementation: Simple rules based on dealer positioning.
        """
        adjustments = {
            'gex_adjustment': 0.0,
            'gamma_wall_bonus': 0.0,
            'dealer_position_adjustment': 0.0
        }
        
        # Check proximity to gamma walls
        if 'gamma_walls' in gex_data and gex_data['gamma_walls']:
            nearest_wall = min(gex_data['gamma_walls'], 
                             key=lambda x: abs(x - spot_price))
            distance_pct = abs(nearest_wall - spot_price) / spot_price
            
            if distance_pct < 0.005:  # Within 0.5% of gamma wall
                adjustments['gamma_wall_bonus'] = 5.0
        
        # Strategy-specific adjustments based on dealer positioning
        dealer_pos = gex_data.get('dealer_position', 'NEUTRAL')
        
        if strategy_type == "Butterfly":
            # Butterflies prefer stable, range-bound markets
            if dealer_pos in ["LONG_GAMMA", "LONG_GAMMA_STRONG"]:
                adjustments['dealer_position_adjustment'] = 4.0
                
        elif strategy_type == "Iron_Condor":
            # Iron Condors also prefer dealer long gamma (dampened volatility)
            if dealer_pos == "LONG_GAMMA":
                adjustments['dealer_position_adjustment'] = 3.0
            elif dealer_pos == "LONG_GAMMA_STRONG":
                adjustments['dealer_position_adjustment'] = 5.0
                
        elif strategy_type == "Vertical":
            # Verticals can benefit from dealer short gamma (trending markets)
            if dealer_pos in ["SHORT_GAMMA", "SHORT_GAMMA_STRONG"]:
                adjustments['dealer_position_adjustment'] = 3.0
        
        # General GEX magnitude adjustment
        gex_magnitude = abs(gex_data.get('net_gex', 0))
        if gex_magnitude > 1e9:  # High GEX environment
            adjustments['gex_adjustment'] = 2.0
        
        return adjustments
    
    def analyze_gex_trend(
        self,
        historical_gex: List[Dict[str, float]],
        lookback: int = 5
    ) -> Dict[str, float]:
        """
        Analyze GEX trend over recent periods.
        
        Simple trend analysis for ship-fast approach.
        """
        if len(historical_gex) < 2:
            return {'trend': 'INSUFFICIENT_DATA', 'change_rate': 0.0}
        
        recent_gex = historical_gex[-lookback:] if len(historical_gex) >= lookback else historical_gex
        
        # Calculate simple moving average
        gex_values = [g.get('net_gex', 0) for g in recent_gex]
        avg_gex = np.mean(gex_values)
        current_gex = gex_values[-1]
        
        # Determine trend
        if current_gex > avg_gex * 1.1:
            trend = 'INCREASING'
        elif current_gex < avg_gex * 0.9:
            trend = 'DECREASING'
        else:
            trend = 'STABLE'
        
        # Calculate rate of change
        if len(gex_values) >= 2:
            change_rate = (gex_values[-1] - gex_values[0]) / max(abs(gex_values[0]), 1)
        else:
            change_rate = 0.0
        
        return {
            'trend': trend,
            'change_rate': change_rate,
            'current_vs_avg': current_gex / avg_gex if avg_gex != 0 else 1.0
        }


# Example usage and testing
if __name__ == "__main__":
    # Test the wrapper
    gex_wrapper = GammaExposureWrapper()
    
    # Mock option chain data
    mock_chain = [
        {
            'strike': 5800,
            'call_gamma': 0.0012,
            'put_gamma': 0.0008,
            'call_open_interest': 5000,
            'put_open_interest': 3000
        },
        {
            'strike': 5850,
            'call_gamma': 0.0018,
            'put_gamma': 0.0015,
            'call_open_interest': 8000,
            'put_open_interest': 6000
        },
        {
            'strike': 5900,
            'call_gamma': 0.0010,
            'put_gamma': 0.0020,
            'call_open_interest': 4000,
            'put_open_interest': 7000
        }
    ]
    
    # Calculate GEX
    spot = 5850
    gex_data = gex_wrapper.calculate_net_gex(mock_chain, spot, is_zero_dte=True)
    
    print("Gamma Exposure Analysis:")
    print(f"Spot Price: {spot}")
    print(f"Net GEX: ${gex_data['net_gex']:,.0f}")
    print(f"Call GEX: ${gex_data['call_gex']:,.0f}")
    print(f"Put GEX: ${gex_data['put_gex']:,.0f}")
    print(f"Dealer Position: {gex_data['dealer_position']}")
    print(f"Gamma Walls: {gex_data['gamma_walls']}")
    print(f"GEX per Point: ${gex_data['gex_per_point']:,.0f}")
    
    # Test strategy adjustments
    for strategy in ["Butterfly", "Iron_Condor", "Vertical"]:
        adj = gex_wrapper.get_strategy_gex_adjustments(strategy, gex_data, spot)
        print(f"\n{strategy} GEX adjustments: {adj}")
