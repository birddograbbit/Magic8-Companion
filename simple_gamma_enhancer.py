#!/usr/bin/env python3
"""
Simple gamma integration for Magic8-Companion
Direct integration without external dependencies
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

from magic8_companion.analysis.gamma.gamma_runner import IntegratedGammaRunner

logger = logging.getLogger(__name__)


class SimpleGammaEnhancer:
    """Simple gamma enhancement for Magic8 - fully integrated"""
    
    def __init__(self):
        # Use integrated gamma runner
        self.gamma_runner = IntegratedGammaRunner()
        self.cache_duration_minutes = 5
        self.last_analysis = {}
        self.last_analysis_time = {}
        
        logger.info("Simple gamma enhancer initialized with integrated analysis")
    
    def get_gamma_adjustment(self, strategy: str, spot_price: float, symbol: str = 'SPX') -> float:
        """
        Get gamma-based score adjustment for a strategy
        
        Args:
            strategy: Strategy name (Butterfly, Iron_Condor, Vertical)
            spot_price: Current spot price
            symbol: Symbol to analyze
        
        Returns:
            Adjustment value (-20 to +20 points)
        """
        # Get gamma analysis
        gamma_data = self._get_or_run_analysis(symbol)
        if not gamma_data:
            return 0.0
        
        # Use pre-calculated adjustments if available
        if 'score_adjustments' in gamma_data:
            base_adjustment = gamma_data['score_adjustments'].get(strategy, 0)
            
            # Apply signal strength modifier if available
            signals = gamma_data.get('signals', {})
            if signals.get('signal_strength') == 'strong':
                base_adjustment *= 1.2
            elif signals.get('signal_strength') == 'weak':
                base_adjustment *= 0.8
            
            return max(-20, min(20, base_adjustment))
        
        # Fallback: Calculate adjustments based on gamma metrics
        return self._calculate_adjustment(strategy, gamma_data, spot_price)
    
    def _get_or_run_analysis(self, symbol: str) -> Optional[Dict]:
        """Get cached analysis or run new one"""
        # Check cache
        if symbol in self.last_analysis and symbol in self.last_analysis_time:
            age = datetime.now() - self.last_analysis_time[symbol]
            if age < timedelta(minutes=self.cache_duration_minutes):
                logger.debug(f"Using cached gamma analysis for {symbol}")
                return self.last_analysis[symbol]
        
        # Run new analysis
        logger.info(f"Running gamma analysis for {symbol}")
        analysis = self.gamma_runner.analyze_gamma(symbol)
        
        if analysis:
            self.last_analysis[symbol] = analysis
            self.last_analysis_time[symbol] = datetime.now()
            return analysis
        
        return None
    
    def _calculate_adjustment(self, strategy: str, gamma_data: Dict, spot_price: float) -> float:
        """Calculate adjustment based on gamma metrics"""
        metrics = gamma_data.get('gamma_metrics', {})
        signals = gamma_data.get('signals', {})
        
        net_gex = metrics.get('net_gex', 0)
        call_wall = metrics.get('call_wall', spot_price + 100)
        put_wall = metrics.get('put_wall', spot_price - 100)
        zero_gamma = metrics.get('gamma_flip', spot_price)
        
        # Calculate distances as percentages
        dist_to_call = (call_wall - spot_price) / spot_price
        dist_to_put = (spot_price - put_wall) / spot_price
        dist_to_zero = abs(spot_price - zero_gamma) / spot_price
        
        # Gamma regime
        positive_gamma = net_gex > 0
        
        # Strategy-specific adjustments
        adjustment = 0.0
        
        if strategy == "Butterfly":
            # Butterflies love positive gamma and pinning
            if positive_gamma:
                adjustment += 10
            if min(dist_to_call, dist_to_put) < 0.005:  # Near wall
                adjustment += 10
            if dist_to_zero < 0.003:  # Near zero gamma
                adjustment += 5
                
        elif strategy == "Iron_Condor":
            # ICs need range-bound conditions
            if positive_gamma:
                adjustment += 8
            # Good range between walls
            if 0.01 < dist_to_call < 0.03 and 0.01 < dist_to_put < 0.03:
                adjustment += 10
            # Too close to walls is bad
            if dist_to_call < 0.005 or dist_to_put < 0.005:
                adjustment -= 15
                
        elif strategy == "Vertical":
            # Verticals like negative gamma for trends
            if not positive_gamma:
                adjustment += 8
            # Near zero gamma = breakout potential
            if dist_to_zero < 0.002:
                adjustment += 10

            # Determine orientation relative to gamma flip
            gamma_flip = metrics.get('gamma_flip', spot_price)
            is_bull = spot_price <= gamma_flip

            # Close to wall in trade direction is bad
            if is_bull:
                if dist_to_call < 0.01:
                    adjustment -= 5  # Resistance nearby
            else:
                if dist_to_put < 0.01:
                    adjustment -= 5  # Support nearby
        
        # Log the adjustment
        if adjustment != 0:
            logger.debug(f"Gamma adjustment for {strategy}: {adjustment:+.0f} "
                        f"(GEX: {net_gex:.1f}B, Regime: {'Positive' if positive_gamma else 'Negative'})")
        
        return max(-20, min(20, adjustment))
    
    def enhance_magic8_scores(self, scores: Dict[str, float], 
                            spot_price: float, symbol: str = 'SPX') -> Dict[str, float]:
        """
        Enhance Magic8 scores with gamma adjustments
        
        Args:
            scores: Original Magic8 scores {'Butterfly': 65, 'Iron_Condor': 70, ...}
            spot_price: Current spot price
            symbol: Symbol being analyzed
            
        Returns:
            Enhanced scores
        """
        enhanced = {}
        
        for strategy, base_score in scores.items():
            adjustment = self.get_gamma_adjustment(strategy, spot_price, symbol)
            
            # Apply adjustment with bounds [0, 100]
            enhanced_score = max(0, min(100, base_score + adjustment))
            enhanced[strategy] = enhanced_score
            
            # Log significant changes
            if abs(adjustment) >= 5:
                logger.info(f"{symbol} {strategy}: {base_score:.0f} → {enhanced_score:.0f} "
                           f"(gamma: {adjustment:+.0f})")
        
        return enhanced
    
    def get_gamma_metrics(self, symbol: str = 'SPX') -> Optional[Dict]:
        """Get key gamma metrics for a symbol"""
        gamma_data = self._get_or_run_analysis(symbol)
        if not gamma_data:
            return None
        
        metrics = gamma_data.get('gamma_metrics', {})
        signals = gamma_data.get('signals', {})
        
        return {
            'net_gex': metrics.get('net_gex', 0),
            'gamma_regime': signals.get('gamma_regime', 'unknown'),
            'market_bias': signals.get('bias', 'neutral'),
            'gamma_flip': metrics.get('gamma_flip', 0),
            'call_wall': metrics.get('call_wall', 0),
            'put_wall': metrics.get('put_wall', 0),
            'confidence': signals.get('confidence', 'medium')
        }


# Quick test function
def test_gamma_enhancement():
    """Test the gamma enhancement"""
    enhancer = SimpleGammaEnhancer()
    
    # Mock scores
    test_scores = {
        'Butterfly': 65,
        'Iron_Condor': 70,
        'Vertical': 60
    }
    
    # Mock spot price
    spot_price = 5900
    
    print("Testing Gamma Enhancement")
    print(f"Spot Price: {spot_price}")
    print(f"Original Scores: {test_scores}")
    
    enhanced = enhancer.enhance_magic8_scores(test_scores, spot_price)
    print(f"Enhanced Scores: {enhanced}")
    
    # Show adjustments
    print("\nAdjustments:")
    for strategy in test_scores:
        adj = enhanced[strategy] - test_scores[strategy]
        if adj != 0:
            print(f"  {strategy}: {adj:+.0f} points")
    
    # Show gamma metrics
    metrics = enhancer.get_gamma_metrics()
    if metrics:
        print(f"\nGamma Metrics:")
        print(f"  Net GEX: ${metrics['net_gex']:,.0f}")
        print(f"  Regime: {metrics['gamma_regime']}")
        print(f"  Bias: {metrics['market_bias']}")
        print(f"  Confidence: {metrics['confidence']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_gamma_enhancement()
