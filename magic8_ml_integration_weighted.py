"""
Enhanced ML Integration for Magic8-Companion with Configurable Weights

This module properly integrates MLOptionTrading predictions with Magic8-Companion
scoring, implementing the ML_WEIGHT and other scoring adjustments.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np

# Add MLOptionTrading to path
ML_PATH = Path(__file__).parent.parent / "MLOptionTrading"
if ML_PATH.exists():
    sys.path.insert(0, str(ML_PATH))

from ml.enhanced_ml_system import ProductionMLSystem, MLConfig

logger = logging.getLogger(__name__)


class WeightedMLScorer:
    """
    Integrates ML predictions with Magic8 scoring using configurable weights.
    
    This implements the weight-based scoring adjustments mentioned in the
    production readiness documentation.
    """
    
    def __init__(self, 
                 ml_weight: float = 0.40,
                 gamma_weight: float = 0.20,
                 base_weight: float = 0.40,
                 min_recommendation_score: int = 65):
        """
        Initialize weighted scorer with configurable weights.
        
        Args:
            ml_weight: Weight for ML predictions (0-1)
            gamma_weight: Weight for gamma analysis (0-1)
            base_weight: Weight for base Magic8 scoring (0-1)
            min_recommendation_score: Minimum score to recommend a strategy
        """
        # Validate weights sum to 1.0
        total_weight = ml_weight + gamma_weight + base_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights sum to {total_weight}, normalizing...")
            self.ml_weight = ml_weight / total_weight
            self.gamma_weight = gamma_weight / total_weight
            self.base_weight = base_weight / total_weight
        else:
            self.ml_weight = ml_weight
            self.gamma_weight = gamma_weight
            self.base_weight = base_weight
        
        self.min_recommendation_score = min_recommendation_score
        
        # Initialize ML system
        try:
            self.ml_config = MLConfig(
                enable_two_stage=True,
                direction_model_path=str(ML_PATH / 'models' / 'direction_model.pkl'),
                volatility_model_path=str(ML_PATH / 'models' / 'volatility_model.pkl')
            )
            self.ml_system = ProductionMLSystem(self.ml_config)
            self.ml_available = True
            logger.info("ML system initialized successfully")
        except Exception as e:
            logger.warning(f"ML system initialization failed: {e}")
            self.ml_available = False
    
    def score_combo_types(self, market_data: Dict, symbol: str, 
                         base_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate weighted scores combining base, ML, and gamma components.
        
        Args:
            market_data: Market data including price, volume, vix, etc.
            symbol: Trading symbol (e.g., 'SPX')
            base_scores: Base scores from Magic8-Companion scorer
            
        Returns:
            Dictionary of weighted scores by strategy type
        """
        # Start with base scores
        weighted_scores = {}
        
        for strategy in base_scores:
            # Base component
            base_component = base_scores[strategy] * self.base_weight
            
            # ML component
            ml_component = 0
            if self.ml_available:
                ml_score = self._get_ml_score(market_data, symbol, strategy)
                ml_component = ml_score * self.ml_weight
            
            # Gamma component (from base scorer's gamma analysis)
            gamma_component = self._get_gamma_score(market_data, strategy) * self.gamma_weight
            
            # Combine components
            weighted_scores[strategy] = base_component + ml_component + gamma_component
            
            logger.debug(
                f"{symbol} {strategy}: base={base_scores[strategy]:.1f} "
                f"({base_component:.1f}), ml={ml_component:.1f}, "
                f"gamma={gamma_component:.1f}, total={weighted_scores[strategy]:.1f}"
            )
        
        return weighted_scores
    
    def _get_ml_score(self, market_data: Dict, symbol: str, strategy: str) -> float:
        """Get ML prediction score for a specific strategy."""
        try:
            # Prepare features for ML prediction
            features = self._prepare_ml_features(market_data)
            
            # Get ML prediction
            prediction, confidence = self.ml_system.predict_strategy(features)
            
            # Convert prediction to score
            if prediction == strategy:
                # ML agrees with this strategy
                return 100 * confidence['overall_confidence']
            elif prediction == "No_Trade":
                # ML suggests no trade
                return 20  # Small penalty
            else:
                # ML suggests different strategy
                return 40  # Moderate score
                
        except Exception as e:
            logger.debug(f"ML prediction failed: {e}")
            return 50  # Neutral score on failure
    
    def _prepare_ml_features(self, market_data: Dict) -> pd.DataFrame:
        """Prepare features for ML prediction from market data."""
        features = {
            'premium': market_data.get('premium', 0),
            'risk': market_data.get('risk', 100),
            'expected_move': market_data.get('expected_range_pct', 0.01) * 100,
            'price': market_data.get('price', 0),
            'volume': market_data.get('volume', 0),
            'high_low_range': market_data.get('high_low_range', 0),
            'vix': market_data.get('vix', 20),
            'delta_spread': market_data.get('delta_spread', 0),
            'price_vs_predicted': market_data.get('price_vs_predicted', 0),
            'call_delta': market_data.get('call_delta', 0),
            'put_delta': market_data.get('put_delta', 0)
        }
        
        return pd.DataFrame([features])
    
    def _get_gamma_score(self, market_data: Dict, strategy: str) -> float:
        """
        Calculate gamma-based score component.
        
        This leverages the gamma analysis already in Magic8-Companion.
        """
        gamma_env = market_data.get('gamma_environment', '').lower()
        
        # Strategy-specific gamma scoring
        if strategy == "Butterfly":
            if "high gamma" in gamma_env or "pinning" in gamma_env:
                return 90
            elif "stable" in gamma_env:
                return 70
            else:
                return 50
                
        elif strategy == "Iron_Condor":
            if "range-bound" in gamma_env or "moderate" in gamma_env:
                return 85
            elif "stable" in gamma_env:
                return 70
            else:
                return 40
                
        elif strategy == "Vertical":
            if "directional" in gamma_env or "variable" in gamma_env:
                return 90
            elif "trending" in gamma_env:
                return 80
            else:
                return 50
        
        return 50  # Default neutral score
    
    def generate_recommendation(self, weighted_scores: Dict[str, float]) -> Dict:
        """Generate recommendation based on weighted scores."""
        if not weighted_scores:
            return {"recommendation": "NONE", "reason": "No scores provided"}
        
        # Find best strategy
        best_strategy = max(weighted_scores, key=weighted_scores.get)
        best_score = weighted_scores[best_strategy]
        
        # Check if meets minimum threshold
        if best_score < self.min_recommendation_score:
            return {
                "recommendation": "NONE", 
                "reason": f"Best score {best_score:.1f} below threshold {self.min_recommendation_score}"
            }
        
        # Check score gap
        scores_list = sorted(weighted_scores.values(), reverse=True)
        if len(scores_list) > 1:
            score_gap = scores_list[0] - scores_list[1]
            if score_gap < 10:  # MIN_SCORE_GAP
                return {
                    "recommendation": "NONE",
                    "reason": f"Insufficient gap ({score_gap:.1f}) between top strategies"
                }
        
        # Determine confidence level
        if best_score >= 80:
            confidence = "HIGH"
        elif best_score >= 70:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return {
            "recommendation": best_strategy,
            "score": best_score,
            "confidence": confidence,
            "ml_weight": self.ml_weight,
            "gamma_weight": self.gamma_weight
        }


def integrate_with_magic8(base_scorer):
    """
    Factory function to wrap Magic8-Companion scorer with ML integration.
    
    Usage in Magic8-Companion:
        from magic8_ml_integration_weighted import integrate_with_magic8
        
        # Wrap existing scorer
        enhanced_scorer = integrate_with_magic8(original_scorer)
        
        # Use enhanced scorer
        scores = enhanced_scorer.score_combo_types(market_data, symbol)
    """
    
    class MLEnhancedScorer:
        def __init__(self, base_scorer):
            self.base_scorer = base_scorer
            self.weighted_scorer = WeightedMLScorer(
                ml_weight=0.40,
                gamma_weight=0.20,
                base_weight=0.40,
                min_recommendation_score=65
            )
        
        async def score_combo_types(self, market_data: Dict, symbol: str) -> Dict[str, float]:
            """Enhanced scoring with ML integration."""
            # Get base scores
            base_scores = await self.base_scorer.score_combo_types(market_data, symbol)
            
            # Apply ML weighting
            weighted_scores = self.weighted_scorer.score_combo_types(
                market_data, symbol, base_scores
            )
            
            return weighted_scores
        
        def generate_recommendation(self, scores: Dict[str, float]) -> Dict:
            """Generate recommendation using weighted scorer."""
            return self.weighted_scorer.generate_recommendation(scores)
    
    return MLEnhancedScorer(base_scorer)


if __name__ == "__main__":
    # Test the weighted scorer
    logger.info("Testing weighted ML scorer...")
    
    scorer = WeightedMLScorer()
    
    # Test market data
    test_market_data = {
        'price': 5000,
        'volume': 1000000,
        'vix': 20,
        'expected_range_pct': 0.01,
        'gamma_environment': 'stable high gamma',
        'premium': 10,
        'risk': 100
    }
    
    # Test base scores
    test_base_scores = {
        'Butterfly': 80,
        'Iron_Condor': 60,
        'Vertical': 50
    }
    
    # Calculate weighted scores
    weighted = scorer.score_combo_types(test_market_data, 'SPX', test_base_scores)
    print(f"Weighted scores: {weighted}")
    
    # Generate recommendation
    rec = scorer.generate_recommendation(weighted)
    print(f"Recommendation: {rec}")
