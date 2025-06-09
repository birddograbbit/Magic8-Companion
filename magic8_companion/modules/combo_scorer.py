"""
Combo scorer for Magic8-Companion.
Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable.
Based on industry best practices for IV percentile thresholds.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ComboScorer:
    """Combo scoring based on market conditions and IV percentile."""
    
    def __init__(self):
        # Research-based scoring parameters
        # Butterfly: Best in low IV environments (IV percentile < 30)
        self.butterfly_thresholds = {
            "iv_percentile_max": 30,      # Below 30th percentile
            "iv_percentile_sweet": 20,    # Ideal below 20th percentile
            "tight_range_max": 0.006,     # 0.6% daily range
            "ultra_tight_range": 0.004,   # 0.4% for bonus points
            "gamma_pinning_bonus": 25
        }
        
        # Iron Condor: Best in moderate IV (30-70 percentile)
        self.iron_condor_thresholds = {
            "iv_percentile_min": 30,      # Above 30th percentile
            "iv_percentile_max": 70,      # Below 70th percentile
            "iv_percentile_sweet": 50,    # Ideal around 50th percentile
            "range_bound_max": 0.010,     # 1.0% daily range
            "moderate_range": 0.008,      # 0.8% ideal range
            "credit_premium_bonus": 20
        }
        
        # Vertical: Best in high IV environments (> 50 percentile)
        self.vertical_thresholds = {
            "iv_percentile_min": 50,      # Above 50th percentile
            "iv_percentile_sweet": 70,    # Better above 70th percentile
            "iv_percentile_high": 85,    # Excellent above 85th percentile
            "wide_range_min": 0.010,      # 1.0% daily range minimum
            "trending_range": 0.015,      # 1.5% for trending markets
            "directional_bonus": 30
        }
    
    def score_combo_types(self, market_data: Dict, symbol: str) -> Dict[str, float]:
        """Score all combo types based on market conditions."""
        logger.debug(f"Scoring combo types for {symbol}")
        
        iv_percentile = market_data.get("iv_percentile", 50)
        range_pct = market_data.get("expected_range_pct", 0.01)
        gamma_env = market_data.get("gamma_environment", "")
        
        scores = {
            "Butterfly": self._score_butterfly(iv_percentile, range_pct, gamma_env),
            "Iron_Condor": self._score_iron_condor(iv_percentile, range_pct, gamma_env),
            "Vertical": self._score_vertical(iv_percentile, range_pct, gamma_env)
        }
        
        logger.debug(f"{symbol} scores: {scores}")
        return scores
    
    def _score_butterfly(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Butterfly favorability based on research."""
        score = 0
        
        # IV Percentile scoring (most important factor)
        if iv_percentile < self.butterfly_thresholds["iv_percentile_sweet"]:
            score += 40  # Excellent conditions
        elif iv_percentile < self.butterfly_thresholds["iv_percentile_max"]:
            score += 25  # Good conditions
        elif iv_percentile < 40:
            score += 10  # Acceptable
        else:
            score += 0   # Not ideal for butterflies
        
        # Expected range scoring
        if range_pct < self.butterfly_thresholds["ultra_tight_range"]:
            score += 35  # Perfect for butterflies
        elif range_pct < self.butterfly_thresholds["tight_range_max"]:
            score += 25  # Very good
        elif range_pct < 0.008:
            score += 15  # Acceptable
        else:
            score += 0   # Too wide for butterflies
        
        # Gamma environment bonus
        if "high gamma" in gamma_env.lower() or "pinning" in gamma_env.lower():
            score += self.butterfly_thresholds["gamma_pinning_bonus"]
        elif "low volatility" in gamma_env.lower():
            score += 15
        
        # Market conditions bonus
        if iv_percentile < 20 and range_pct < 0.005:
            score += 10  # Perfect butterfly conditions
        
        return min(score, 100)
    
    def _score_iron_condor(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Iron Condor (Sonar) favorability based on research."""
        score = 0
        
        # IV Percentile scoring (sweet spot 30-70)
        if (self.iron_condor_thresholds["iv_percentile_min"] <= iv_percentile <= 
            self.iron_condor_thresholds["iv_percentile_max"]):
            # Peak score around 50th percentile
            distance_from_ideal = abs(iv_percentile - self.iron_condor_thresholds["iv_percentile_sweet"])
            if distance_from_ideal <= 10:
                score += 35  # Perfect range
            elif distance_from_ideal <= 20:
                score += 25  # Good range
            else:
                score += 15  # Acceptable range
        elif 25 <= iv_percentile <= 75:
            score += 10  # Marginally acceptable
        else:
            score += 0   # Outside ideal range
        
        # Range-bound market scoring
        if range_pct < self.iron_condor_thresholds["moderate_range"]:
            score += 30  # Ideal range
        elif range_pct < self.iron_condor_thresholds["range_bound_max"]:
            score += 20  # Good range
        elif range_pct < 0.012:
            score += 10  # Acceptable
        else:
            score += 0   # Too wide
        
        # Credit premium collection bonus (higher IV = more premium)
        if 40 <= iv_percentile <= 60:
            score += self.iron_condor_thresholds["credit_premium_bonus"]
        elif 30 <= iv_percentile <= 70:
            score += 10
        
        # Gamma environment
        if "range-bound" in gamma_env.lower() or "moderate" in gamma_env.lower():
            score += 15
        
        return min(score, 100)
    
    def _score_vertical(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Vertical spread favorability based on research."""
        score = 0
        
        # IV Percentile scoring (higher is better for credit spreads)
        if iv_percentile >= self.vertical_thresholds["iv_percentile_high"]:
            score += 40  # Excellent for credit spreads
        elif iv_percentile >= self.vertical_thresholds["iv_percentile_sweet"]:
            score += 30  # Very good
        elif iv_percentile >= self.vertical_thresholds["iv_percentile_min"]:
            score += 20  # Good
        elif iv_percentile >= 40:
            score += 10  # Acceptable
        else:
            score += 0   # Too low for good credit spreads
        
        # Wide expected range (directional movement)
        if range_pct >= self.vertical_thresholds["trending_range"]:
            score += 35  # Trending market
        elif range_pct >= self.vertical_thresholds["wide_range_min"]:
            score += 25  # Good movement expected
        elif range_pct >= 0.008:
            score += 15  # Some movement
        else:
            score += 5   # Limited movement expected
        
        # Directional gamma environment
        if "directional" in gamma_env.lower() or "variable" in gamma_env.lower():
            score += self.vertical_thresholds["directional_bonus"]
        elif "high volatility" in gamma_env.lower():
            score += 20
        elif "trending" in gamma_env.lower():
            score += 15
        
        # High IV bonus for premium collection
        if iv_percentile > 80 and range_pct > 0.012:
            score += 10  # Excellent vertical conditions
        
        return min(score, 100)
