"""
Simplified combo scorer for Magic8-Companion.
Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ComboScorer:
    """Simplified combo scoring based on market conditions."""
    
    def __init__(self):
        # Scoring parameters
        self.butterfly_thresholds = {
            "low_iv_max": 40,
            "tight_range_max": 0.006,
            "pinning_bonus": 20
        }
        
        self.iron_condor_thresholds = {
            "moderate_iv_min": 30,
            "moderate_iv_max": 80,
            "range_bound_max": 0.012,
            "neutral_bonus": 15
        }
        
        self.vertical_thresholds = {
            "high_iv_min": 50,
            "wide_range_min": 0.010,
            "directional_bonus": 25
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
        """Score Butterfly favorability."""
        score = 0
        
        # Low IV environment favors butterflies
        if iv_percentile < self.butterfly_thresholds["low_iv_max"]:
            score += 30
        elif iv_percentile < 60:
            score += 15
        
        # Tight expected range favors butterflies
        if range_pct < self.butterfly_thresholds["tight_range_max"]:
            score += 35
        elif range_pct < 0.010:
            score += 20
        
        # Gamma pinning environment
        if "high gamma" in gamma_env.lower() or "pinning" in gamma_env.lower():
            score += self.butterfly_thresholds["pinning_bonus"]
        
        # Low volatility bonus
        if "low volatility" in gamma_env.lower():
            score += 15
        
        return min(score, 100)
    
    def _score_iron_condor(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Iron Condor (Sonar) favorability."""
        score = 0
        
        # Moderate IV environment
        if (self.iron_condor_thresholds["moderate_iv_min"] <= 
            iv_percentile <= self.iron_condor_thresholds["moderate_iv_max"]):
            score += 25
        
        # Range-bound market
        if range_pct < self.iron_condor_thresholds["range_bound_max"]:
            score += 30
        elif range_pct < 0.015:
            score += 15
        
        # Neutral gamma environment
        if "range-bound" in gamma_env.lower() or "moderate" in gamma_env.lower():
            score += self.iron_condor_thresholds["neutral_bonus"]
        
        # Credit spread benefit in higher IV
        if iv_percentile > 40:
            score += 20
        
        return min(score, 100)
    
    def _score_vertical(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Vertical spread favorability."""
        score = 0
        
        # Higher IV for credit spreads
        if iv_percentile > self.vertical_thresholds["high_iv_min"]:
            score += 25
        elif iv_percentile > 40:
            score += 10
        
        # Wide expected range (directional movement)
        if range_pct > self.vertical_thresholds["wide_range_min"]:
            score += 30
        elif range_pct > 0.008:
            score += 15
        
        # Directional gamma environment
        if "directional" in gamma_env.lower() or "variable" in gamma_env.lower():
            score += self.vertical_thresholds["directional_bonus"]
        
        # High volatility environment
        if "high volatility" in gamma_env.lower():
            score += 20
        
        return min(score, 100)
