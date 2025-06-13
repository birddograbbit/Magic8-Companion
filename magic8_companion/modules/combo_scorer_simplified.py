"""
Simplified combo scorer for Magic8-Companion.
Determines which trade type (Butterfly, Iron Condor, Vertical) is most favorable.
Made MORE GENEROUS to reduce conservative bias.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ComboScorer:
    """Simplified combo scoring based on market conditions with MORE LENIENT thresholds."""
    
    def __init__(self):
        # MORE LENIENT THRESHOLDS
        self.butterfly_thresholds = {
            "low_iv_max": 50,          # Up from 40
            "tight_range_max": 0.008,  # Up from 0.006
            "pinning_bonus": 25        # Up from 20
        }
        
        self.iron_condor_thresholds = {
            "moderate_iv_min": 25,     # Down from 30
            "moderate_iv_max": 85,     # Up from 80
            "range_bound_max": 0.015,  # Up from 0.012
            "neutral_bonus": 20        # Up from 15
        }
        
        self.vertical_thresholds = {
            "high_iv_min": 40,         # Down from 50
            "wide_range_min": 0.008,   # Down from 0.010
            "directional_bonus": 30    # Up from 25
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
        """Score Butterfly favorability with MORE GENEROUS scoring."""
        score = 0
        
        # MORE GENEROUS IV SCORING
        if iv_percentile < 35:
            score += 40  # Up from 30
        elif iv_percentile < 50:
            score += 30  # New tier
        elif iv_percentile < 65:
            score += 20  # Was 15
        else:
            score += 10  # Still give some points
        
        # RANGE SCORING
        if range_pct < 0.005:
            score += 40  # Up from 35
        elif range_pct < 0.008:
            score += 30  # New tier
        elif range_pct < 0.012:
            score += 20  # Was excluded
        else:
            score += 10  # Still give some points
        
        # GAMMA BONUS
        if "high gamma" in gamma_env.lower() or "pinning" in gamma_env.lower():
            score += self.butterfly_thresholds["pinning_bonus"]
        elif "low volatility" in gamma_env.lower():
            score += 20  # Up from 15
        else:
            score += 10  # Default bonus
        
        return min(score, 100)
    
    def _score_iron_condor(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Iron Condor (Sonar) favorability with MORE LENIENT scoring."""
        score = 0
        
        # MORE LENIENT IV RANGE
        if (self.iron_condor_thresholds["moderate_iv_min"] <= 
            iv_percentile <= self.iron_condor_thresholds["moderate_iv_max"]):
            score += 35  # Up from 25
        elif 20 <= iv_percentile <= 90:
            score += 20  # Extended range
        else:
            score += 10  # Still give some points
        
        # RANGE SCORING
        if range_pct < 0.010:
            score += 35  # Up from 30
        elif range_pct < self.iron_condor_thresholds["range_bound_max"]:
            score += 25  # Up from 15
        else:
            score += 15  # Still give points
        
        # ENVIRONMENT BONUS
        if "range-bound" in gamma_env.lower() or "moderate" in gamma_env.lower():
            score += self.iron_condor_thresholds["neutral_bonus"]
        else:
            score += 10  # Default bonus
        
        # BASE CREDIT FOR IC - always viable
        score += 15  # New base points
        
        return min(score, 100)
    
    def _score_vertical(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Vertical spread favorability with MORE GENEROUS requirements."""
        score = 0
        
        # MORE GENEROUS IV SCORING
        if iv_percentile > 60:
            score += 35  # Up from 25
        elif iv_percentile > self.vertical_thresholds["high_iv_min"]:
            score += 25  # Up from 10
        else:
            score += 15  # Always viable
        
        # RANGE SCORING
        if range_pct > 0.012:
            score += 35  # Up from 30
        elif range_pct > self.vertical_thresholds["wide_range_min"]:
            score += 25  # Up from 15
        else:
            score += 15  # Can work in any range
        
        # ENVIRONMENT BONUS
        if "directional" in gamma_env.lower() or "variable" in gamma_env.lower():
            score += self.vertical_thresholds["directional_bonus"]
        elif "high volatility" in gamma_env.lower():
            score += 25  # Up from 20
        else:
            score += 15  # Default bonus
        
        # BASE POINTS - verticals are versatile
        score += 15  # New base points
        
        return min(score, 100)
