# magic8_ml_integration.py
"""
Magic8-Companion ML Integration Helper
Copy this file to Magic8-Companion directory for easy ML integration
"""

import sys
import os
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MLEnhancedScoring:
    """
    Drop-in replacement for Magic8-Companion scorer with ML enhancement
    """
    
    def __init__(self, base_scorer, ml_option_trading_path: str = "../MLOptionTrading"):
        """
        Initialize ML-enhanced scorer
        
        Args:
            base_scorer: Original Magic8 scorer instance
            ml_option_trading_path: Path to MLOptionTrading repository
        """
        self.base_scorer = base_scorer
        # Convert to absolute path to ensure it works regardless of working directory
        self.ml_path = Path(ml_option_trading_path).resolve()
        self.ml_system = None
        self.ml_weight = 0.35  # 35% ML, 65% rules
        
        # Try to load ML system
        self._load_ml_system()
        
    def _load_ml_system(self):
        """Load ML system if available"""
        try:
            # Add ML path to Python path
            ml_path_str = str(self.ml_path)
            if ml_path_str not in sys.path:
                sys.path.insert(0, ml_path_str)
            
            # Import ML components
            from ml.enhanced_ml_system import ProductionMLSystem, MLConfig
            from ml.discord_data_processor import DiscordDataLoader
            
            # Check if models exist
            models_dir = self.ml_path / "models"
            if not models_dir.exists():
                logger.warning(f"ML models directory not found at {models_dir}. Run training first.")
                return
            
            # Construct absolute paths to model files
            direction_model_path = (models_dir / "direction_model.pkl").resolve()
            volatility_model_path = (models_dir / "volatility_model.pkl").resolve()
            
            # Verify model files exist
            if not direction_model_path.exists():
                logger.warning(f"Direction model not found at {direction_model_path}")
                return
            if not volatility_model_path.exists():
                logger.warning(f"Volatility model not found at {volatility_model_path}")
                return
            
            logger.info(f"Loading models from {models_dir}")
            logger.info(f"Direction model: {direction_model_path}")
            logger.info(f"Volatility model: {volatility_model_path}")
            
            # Initialize ML system with absolute paths
            config = MLConfig(
                enable_two_stage=True,
                use_vectorized_greeks=True,
                confidence_threshold=0.65,
                direction_model_path=str(direction_model_path),
                volatility_model_path=str(volatility_model_path)
            )
            
            self.ml_system = ProductionMLSystem(config)
            
            # Initialize data loader with absolute path
            processed_parquet_path = (self.ml_path / "temp_exports" / "processed_parquet").resolve()
            self.data_loader = DiscordDataLoader(str(processed_parquet_path))
            
            logger.info("ML system loaded successfully")
            logger.info(f"ML path: {self.ml_path}")
            logger.info(f"Models loaded from: {models_dir}")
            
        except ImportError as e:
            logger.warning(f"Could not import ML components: {e}")
            logger.info("ML enhancement disabled. Using rule-based scoring only.")
        except Exception as e:
            logger.error(f"Error loading ML system: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("ML enhancement disabled. Using rule-based scoring only.")
    
    async def score_combo_types(self, market_data: Dict, symbol: str) -> Dict[str, float]:
        """
        Enhanced scoring with ML integration
        
        Args:
            market_data: Market data dictionary
            symbol: Trading symbol (e.g., 'SPX')
            
        Returns:
            Dictionary of strategy scores
        """
        # Get base rule-based scores - now await the async method
        base_scores = await self.base_scorer.score_combo_types(market_data, symbol)
        
        # If ML system not loaded, return base scores
        if self.ml_system is None:
            return base_scores
        
        try:
            # Prepare data for ML prediction
            ml_data = self._prepare_ml_data(market_data, symbol)
            
            # Get ML prediction
            ml_result = self.ml_system.predict(
                discord_delta=ml_data.get('discord_delta', pd.DataFrame()),
                discord_trades=ml_data.get('discord_trades', pd.DataFrame()),
                bar_data=ml_data.get('bar_data', pd.DataFrame()),
                vix_data=ml_data.get('vix_data', pd.DataFrame()),
                current_time=datetime.now()
            )
            
            # Create ML scores
            ml_scores = self._create_ml_scores(ml_result)
            
            # Combine scores
            combined_scores = self._combine_scores(base_scores, ml_scores)
            
            # Log ML contribution
            logger.info(f"ML prediction: {ml_result['strategy']} "
                       f"(conf: {ml_result['confidence']:.2f})")
            logger.info(f"Score combination - Base: {base_scores}, "
                       f"ML: {ml_scores}, Combined: {combined_scores}")
            
            return combined_scores
            
        except Exception as e:
            logger.error(f"Error in ML scoring: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fall back to base scores
            return base_scores
    
    def _prepare_ml_data(self, market_data: Dict, symbol: str) -> Dict:
        """Prepare data for ML prediction"""
        ml_data = {}
        
        # Convert market data to ML format
        current_time = datetime.now()
        date_str = current_time.strftime('%Y-%m-%d')
        
        # Try to load recent Discord data if available
        try:
            # Load recent delta data
            delta_data = self.data_loader.load_date_range(
                date_str, date_str, 'delta'
            )
            if not delta_data.empty and 'Symbol' in delta_data.columns:
                ml_data['discord_delta'] = delta_data[delta_data['Symbol'] == symbol]
            
            # Load recent trades
            trades_data = self.data_loader.load_date_range(
                date_str, date_str, 'trades'
            )
            if not trades_data.empty and 'Symbol' in trades_data.columns:
                ml_data['discord_trades'] = trades_data[trades_data['Symbol'] == symbol]
                
        except Exception as e:
            logger.debug(f"Could not load Discord data: {e}")
        
        # Convert market data to bar format
        if 'price' in market_data:
            # Create synthetic bar data from current market data
            bar_data = pd.DataFrame([{
                'open': market_data.get('price', 0),
                'high': market_data.get('high', market_data.get('price', 0)),
                'low': market_data.get('low', market_data.get('price', 0)),
                'close': market_data.get('price', 0),
                'volume': market_data.get('volume', 0)
            }], index=[current_time])
            ml_data['bar_data'] = bar_data
        
        # Add VIX data if available
        if 'vix' in market_data:
            vix_data = pd.DataFrame([{
                'close': market_data['vix']
            }], index=[current_time])
            ml_data['vix_data'] = vix_data
        
        return ml_data
    
    def _create_ml_scores(self, ml_result: Dict) -> Dict[str, float]:
        """Convert ML prediction to scores"""
        ml_scores = {
            'Butterfly': 0.0,
            'Iron_Condor': 0.0,
            'Vertical': 0.0
        }
        
        predicted_strategy = ml_result['strategy']
        confidence = ml_result['confidence']
        
        if predicted_strategy in ml_scores:
            # Give high score to ML-predicted strategy
            ml_scores[predicted_strategy] = confidence * 100
            
            # Give smaller scores to related strategies
            if predicted_strategy == 'Butterfly':
                ml_scores['Iron_Condor'] = confidence * 30
            elif predicted_strategy == 'Iron_Condor':
                ml_scores['Butterfly'] = confidence * 30
            elif predicted_strategy == 'Vertical':
                # Verticals are distinct, give minimal score to others
                ml_scores['Butterfly'] = confidence * 20
                ml_scores['Iron_Condor'] = confidence * 20
        
        return ml_scores
    
    def _combine_scores(self, base_scores: Dict[str, float], 
                       ml_scores: Dict[str, float]) -> Dict[str, float]:
        """Combine rule-based and ML scores"""
        combined_scores = {}
        
        for strategy in base_scores:
            base = base_scores[strategy]
            ml = ml_scores.get(strategy, 50)  # Default to neutral
            
            # Weighted combination
            combined = (1 - self.ml_weight) * base + self.ml_weight * ml
            
            # Boost if both agree strongly
            if base > 70 and ml > 70:
                combined = min(combined * 1.15, 100)
            
            # Penalize if they strongly disagree
            if (base > 70 and ml < 30) or (base < 30 and ml > 70):
                combined *= 0.85
            
            combined_scores[strategy] = min(combined, 100)
        
        return combined_scores
    
    def set_ml_weight(self, weight: float):
        """
        Adjust ML contribution weight
        
        Args:
            weight: ML weight (0.0 to 1.0)
        """
        self.ml_weight = max(0.0, min(1.0, weight))
        logger.info(f"ML weight set to {self.ml_weight:.0%}")


# Example usage for Magic8-Companion (for demonstration only)
if __name__ == "__main__":
    # WARNING: This demo code shows how to integrate with Magic8.
    # Do NOT run this block in production environments.
    
    # Mock base scorer for demonstration
    class MockScorer:
        async def score_combo_types(self, market_data, symbol):
            return {
                'Butterfly': 65,
                'Iron_Condor': 55,
                'Vertical': 45
            }
    
    # Create enhanced scorer
    base_scorer = MockScorer()
    enhanced_scorer = MLEnhancedScoring(base_scorer)
    
    # Mock market data
    market_data = {
        'price': 6000,
        'vix': 16.5,
        'volume': 1000000
    }
    
    # Get enhanced scores
    import asyncio
    scores = asyncio.run(enhanced_scorer.score_combo_types(market_data, 'SPX'))
    print(f"Enhanced scores: {scores}")
    
    # Adjust ML weight if needed
    enhanced_scorer.set_ml_weight(0.5)  # 50% ML, 50% rules
