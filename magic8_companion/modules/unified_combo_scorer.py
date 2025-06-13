"""
Unified Combo Scorer - Consolidates all 3 existing scorers into one flexible implementation.

This replaces:
- combo_scorer.py
- combo_scorer_simplified.py  
- enhanced_combo_scorer.py

Provides configuration-driven complexity levels for production use.
"""
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ScorerComplexity(Enum):
    """Complexity modes for the unified scorer."""
    SIMPLE = "simple"      # Basic logic, minimal parameters
    STANDARD = "standard"   # Full research-based logic (current combo_scorer.py)
    ENHANCED = "enhanced"   # Adds Greeks, GEX, Volume analysis


class UnifiedComboScorer:
    """
    Unified combo scorer that replaces all 3 existing scorers.
    
    Provides configuration-driven complexity levels and optional enhancements.
    Made MORE GENEROUS to reduce overly conservative behavior.
    """
    
    def __init__(self, complexity: ScorerComplexity = ScorerComplexity.STANDARD):
        """Initialize unified scorer with specified complexity level."""
        self.complexity = complexity
        
        # Configure thresholds based on complexity mode
        if complexity == ScorerComplexity.SIMPLE:
            self._setup_simple_thresholds()
        elif complexity == ScorerComplexity.STANDARD:
            self._setup_standard_thresholds()
        elif complexity == ScorerComplexity.ENHANCED:
            self._setup_enhanced_thresholds()
            self._initialize_enhancements()
    
    def _setup_simple_thresholds(self):
        """Simple scoring thresholds (current combo_scorer_simplified.py logic)."""
        self.butterfly_thresholds = {
            "low_iv_max": 50,
            "tight_range_max": 0.008,
            "pinning_bonus": 25
        }
        
        self.iron_condor_thresholds = {
            "moderate_iv_min": 25,
            "moderate_iv_max": 85,
            "range_bound_max": 0.015,
            "neutral_bonus": 20
        }
        
        self.vertical_thresholds = {
            "high_iv_min": 40,
            "wide_range_min": 0.008,
            "directional_bonus": 30
        }
    
    def _setup_standard_thresholds(self):
        """Standard scoring thresholds (current combo_scorer.py logic)."""
        self.butterfly_thresholds = {
            "low_iv_max": 50,
            "tight_range_max": 0.008,
            "pinning_bonus": 25,
            # Additional detailed parameters for standard mode
            "iv_sweet_spot": 35,
            "ultra_tight_range": 0.005,
            "gamma_bonus": 20
        }
        
        self.iron_condor_thresholds = {
            "moderate_iv_min": 25,
            "moderate_iv_max": 85,
            "range_bound_max": 0.015,
            "neutral_bonus": 20,
            # Additional detailed parameters
            "iv_sweet_spot": 50,
            "ideal_range": 0.010,
            "credit_bonus": 15
        }
        
        self.vertical_thresholds = {
            "high_iv_min": 40,
            "wide_range_min": 0.008,
            "directional_bonus": 30,
            # Additional detailed parameters
            "iv_sweet_spot": 60,
            "trending_range": 0.012,
            "volatility_bonus": 25
        }
    
    def _setup_enhanced_thresholds(self):
        """Enhanced scoring with additional indicators."""
        # Start with standard thresholds
        self._setup_standard_thresholds()
        
        # Enhanced scoring will add adjustments on top
        self.enhancement_weights = {
            "greeks_weight": 0.15,
            "gex_weight": 0.10,
            "volume_weight": 0.05
        }
    
    def _initialize_enhancements(self):
        """Initialize enhanced indicators if enabled."""
        from magic8_companion.config import settings
        
        self.enable_greeks = getattr(settings, 'enable_greeks', False)
        self.enable_advanced_gex = getattr(settings, 'enable_advanced_gex', False)
        self.enable_enhanced_gex = getattr(settings, 'enable_enhanced_gex', False)
        self.enable_volume_analysis = getattr(settings, 'enable_volume_analysis', False)
        
        # Initialize wrappers only if enhancements are enabled
        if self.enable_greeks:
            try:
                from magic8_companion.wrappers import GreeksWrapper
                self.greeks_wrapper = GreeksWrapper()
                logger.info("Greeks wrapper initialized")
            except ImportError:
                logger.warning("Greeks wrapper not available")
                self.enable_greeks = False
                
        if self.enable_advanced_gex or self.enable_enhanced_gex:
            try:
                # Try enhanced GEX wrapper first
                from magic8_companion.wrappers.enhanced_gex_wrapper import EnhancedGEXWrapper
                self.enhanced_gex_wrapper = EnhancedGEXWrapper()
                logger.info("Enhanced GEX wrapper initialized")
            except ImportError:
                logger.warning("Enhanced GEX wrapper not available, trying standard GEX")
                try:
                    from magic8_companion.wrappers import GammaExposureWrapper
                    self.gex_wrapper = GammaExposureWrapper()
                    logger.info("Standard GEX wrapper initialized")
                except ImportError:
                    logger.warning("No GEX wrapper available")
                    self.enable_advanced_gex = False
                    self.enable_enhanced_gex = False
                
        if self.enable_volume_analysis:
            try:
                from magic8_companion.wrappers import VolumeOIWrapper
                self.volume_wrapper = VolumeOIWrapper()
                logger.info("Volume wrapper initialized")
            except ImportError:
                logger.warning("Volume wrapper not available")
                self.enable_volume_analysis = False
    
    def score_combo_types(self, market_data: Dict, symbol: str) -> Dict[str, float]:
        """
        Score all combo types based on market conditions.
        
        Returns unified scores regardless of complexity mode.
        """
        logger.debug(f"Scoring combo types for {symbol} (mode: {self.complexity.value})")
        
        iv_percentile = market_data.get("iv_percentile", 50)
        range_pct = market_data.get("expected_range_pct", 0.01)
        gamma_env = market_data.get("gamma_environment", "")
        
        # Get base scores using appropriate complexity level
        scores = {
            "Butterfly": self._score_butterfly(iv_percentile, range_pct, gamma_env),
            "Iron_Condor": self._score_iron_condor(iv_percentile, range_pct, gamma_env),
            "Vertical": self._score_vertical(iv_percentile, range_pct, gamma_env)
        }
        
        # Apply enhancements if in enhanced mode
        if self.complexity == ScorerComplexity.ENHANCED:
            scores = self._apply_enhancements(scores, market_data, symbol)
        
        logger.debug(f"{symbol} scores ({self.complexity.value}): {scores}")
        return scores
    
    def _score_butterfly(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Butterfly strategy with mode-appropriate complexity."""
        score = 0
        
        # MORE GENEROUS IV SCORING
        if iv_percentile < 35:
            score += 40
        elif iv_percentile < 50:
            score += 30
        elif iv_percentile < 65:
            score += 20
        else:
            score += 10  # Still give some points
        
        # RANGE SCORING
        if range_pct < 0.005:
            score += 40
        elif range_pct < 0.008:
            score += 30
        elif range_pct < 0.012:
            score += 20
        else:
            score += 10  # Still give some points
        
        # GAMMA BONUS
        if "high gamma" in gamma_env.lower() or "pinning" in gamma_env.lower():
            score += 25
        elif "low volatility" in gamma_env.lower():
            score += 20
        else:
            score += 10  # Default bonus
        
        return min(score, 100)
    
    def _score_iron_condor(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Iron Condor strategy with mode-appropriate complexity."""
        score = 0
        
        # MORE LENIENT IV RANGE
        if 25 <= iv_percentile <= 85:
            if 40 <= iv_percentile <= 60:
                score += 40  # Sweet spot
            else:
                score += 30  # Still good
        else:
            score += 15  # Outside range but not zero
        
        # RANGE SCORING
        if range_pct < 0.010:
            score += 35
        elif range_pct < 0.015:
            score += 25
        else:
            score += 15  # Still give points
        
        # ENVIRONMENT
        if "range-bound" in gamma_env.lower() or "moderate" in gamma_env.lower():
            score += 25
        else:
            score += 15  # Default bonus
        
        # BASE CREDIT FOR IC
        score += 15  # Iron Condors always get base points
        
        return min(score, 100)
    
    def _score_vertical(self, iv_percentile: float, range_pct: float, gamma_env: str) -> float:
        """Score Vertical strategy with mode-appropriate complexity."""
        score = 0
        
        # IV SCORING
        if iv_percentile > 60:
            score += 35
        elif iv_percentile > 40:
            score += 25
        else:
            score += 15  # Still viable
        
        # RANGE SCORING
        if range_pct > 0.012:
            score += 35
        elif range_pct > 0.008:
            score += 25
        else:
            score += 15  # Can work in any range
        
        # ENVIRONMENT
        if "directional" in gamma_env.lower() or "variable" in gamma_env.lower():
            score += 30
        elif "high volatility" in gamma_env.lower():
            score += 25
        else:
            score += 15  # Default
        
        # BASE POINTS FOR VERTICALS
        score += 15  # They're versatile
        
        return min(score, 100)
    
    def _apply_enhancements(self, base_scores: Dict[str, float], 
                          market_data: Dict, symbol: str) -> Dict[str, float]:
        """Apply enhanced indicators to base scores."""
        enhanced_scores = base_scores.copy()
        
        try:
            # Apply Greeks adjustments
            if hasattr(self, 'greeks_wrapper'):
                greeks_adj = self._calculate_greeks_adjustments(market_data)
                for strategy in enhanced_scores:
                    enhanced_scores[strategy] += greeks_adj.get(strategy, 0)
            
            # Apply GEX adjustments (enhanced or standard)
            if hasattr(self, 'enhanced_gex_wrapper') or hasattr(self, 'gex_wrapper'):
                gex_adj = self._calculate_gex_adjustments(market_data)
                for strategy in enhanced_scores:
                    enhanced_scores[strategy] += gex_adj.get(strategy, 0)
            
            # Apply Volume/OI adjustments
            if hasattr(self, 'volume_wrapper'):
                volume_adj = self._calculate_volume_adjustments(market_data)
                for strategy in enhanced_scores:
                    enhanced_scores[strategy] += volume_adj.get(strategy, 0)
                    
        except Exception as e:
            logger.warning(f"Enhancement calculation failed for {symbol}: {e}")
        
        # Ensure scores stay in valid range
        for strategy in enhanced_scores:
            enhanced_scores[strategy] = max(0, min(100, enhanced_scores[strategy]))
        
        return enhanced_scores
    
    def _calculate_greeks_adjustments(self, market_data: Dict) -> Dict[str, float]:
        """Calculate Greeks-based scoring adjustments."""
        # Placeholder - would implement actual Greeks logic here
        return {"Butterfly": 0, "Iron_Condor": 0, "Vertical": 0}
    
    def _calculate_gex_adjustments(self, market_data: Dict) -> Dict[str, float]:
        """Calculate GEX-based scoring adjustments using enhanced gamma analysis."""
        
        try:
            # Try enhanced GEX wrapper first if available
            if hasattr(self, 'enhanced_gex_wrapper'):
                # Get gamma adjustments from MLOptionTrading
                gamma_data = self.enhanced_gex_wrapper.get_gamma_adjustments()
                
                if gamma_data:
                    # Apply sophisticated adjustments from MLOptionTrading
                    adjustments = {}
                    for strategy in ['Butterfly', 'Iron_Condor', 'Vertical']:
                        adj = self.enhanced_gex_wrapper.calculate_strategy_adjustments(
                            strategy, gamma_data
                        )
                        adjustments[strategy] = adj
                    
                    # Log gamma metrics for transparency
                    metrics = self.enhanced_gex_wrapper.get_gamma_metrics(gamma_data)
                    logger.info(
                        f"Enhanced GEX adjustments - Regime: {metrics['regime']}, "
                        f"Bias: {metrics['bias']}, Net GEX: ${metrics['net_gex']:,.0f}"
                    )
                    
                    return adjustments
                else:
                    logger.debug("No fresh gamma data available from MLOptionTrading")
            
            # Fallback to standard GEX wrapper if available
            if hasattr(self, 'gex_wrapper'):
                # Use the existing simple GEX implementation
                return {"Butterfly": 0, "Iron_Condor": 0, "Vertical": 0}
                
        except Exception as e:
            logger.warning(f"GEX adjustment calculation failed: {e}")
        
        # Return zero adjustments if calculation fails
        return {"Butterfly": 0, "Iron_Condor": 0, "Vertical": 0}
    
    def _calculate_volume_adjustments(self, market_data: Dict) -> Dict[str, float]:
        """Calculate Volume/OI-based scoring adjustments."""
        # Placeholder - would implement actual Volume logic here
        return {"Butterfly": 0, "Iron_Condor": 0, "Vertical": 0}


# Factory function for easy usage
def create_scorer(mode: str = "standard") -> UnifiedComboScorer:
    """
    Factory function to create scorer with specified mode.
    
    Args:
        mode: "simple", "standard", or "enhanced"
    
    Returns:
        UnifiedComboScorer instance
    """
    complexity_map = {
        "simple": ScorerComplexity.SIMPLE,
        "standard": ScorerComplexity.STANDARD,
        "enhanced": ScorerComplexity.ENHANCED
    }
    
    return UnifiedComboScorer(complexity_map.get(mode, ScorerComplexity.STANDARD))


# Backward compatibility aliases for existing imports
class ComboScorer(UnifiedComboScorer):
    """Backward compatibility for existing imports."""
    def __init__(self):
        super().__init__(ScorerComplexity.STANDARD)


def generate_recommendation(scores: Dict[str, float]) -> Dict[str, str]:
    """Generate combo type recommendation based on score thresholds."""
    from magic8_companion.config import settings

    if not scores:
        return {"recommendation": "NONE", "reason": "No scores provided"}

    best_combo = max(scores, key=scores.get)
    best_score = scores[best_combo]

    if best_score >= settings.min_recommendation_score:
        second_best = sorted(scores.values())[-2] if len(scores) > 1 else 0
        if best_score - second_best >= settings.min_score_gap:
            return {
                "recommendation": best_combo,
                "score": best_score,
                "confidence": "HIGH" if best_score >= 75 else "MEDIUM",  # Lowered from 85
            }

    return {"recommendation": "NONE", "reason": "No clear favorite"}
