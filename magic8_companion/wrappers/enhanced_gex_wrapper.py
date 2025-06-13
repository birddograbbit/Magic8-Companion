"""
Enhanced GEX wrapper that integrates MLOptionTrading's gamma analysis
Provides seamless integration between MLOptionTrading and Magic8-Companion
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EnhancedGEXWrapper:
    """
    Wrapper that can use either:
    1. Direct integration with MLOptionTrading gamma module
    2. JSON file reading from MLOptionTrading output
    """
    
    def __init__(self, mode='file', ml_option_path=None):
        """
        Initialize enhanced GEX wrapper
        
        Args:
            mode: 'integrated' for direct module import or 'file' for JSON reading
            ml_option_path: Path to MLOptionTrading directory
        """
        self.mode = mode
        self.ml_option_path = ml_option_path or os.getenv('ML_OPTION_TRADING_PATH', '../MLOptionTrading')
        self.gamma_analyzer = None
        
        if mode == 'integrated' and self.ml_option_path:
            try:
                # Add MLOptionTrading to path
                sys.path.insert(0, str(Path(self.ml_option_path).resolve()))
                from analysis.gamma.gamma_exposure import GammaExposureAnalyzer
                self.gamma_analyzer = GammaExposureAnalyzer()
                logger.info("Enhanced GEX wrapper initialized in integrated mode")
            except ImportError as e:
                logger.warning(f"Failed to import gamma analyzer: {e}")
                logger.warning("Falling back to file mode")
                self.mode = 'file'
        
        if self.mode == 'file':
            logger.info("Enhanced GEX wrapper initialized in file mode")
    
    def get_gamma_adjustments(self, symbol='SPX', max_age_minutes=5) -> Optional[Dict]:
        """
        Get gamma adjustments either directly or from file
        
        Args:
            symbol: Symbol to get adjustments for (default: SPX)
            max_age_minutes: Maximum age of data to consider valid
            
        Returns:
            Dictionary with gamma adjustments or None if unavailable
        """
        if self.mode == 'integrated' and self.gamma_analyzer:
            # Direct calculation (future enhancement)
            logger.debug("Direct gamma calculation not yet implemented")
            return self._read_gamma_adjustments(max_age_minutes)
        else:
            # Read from file
            return self._read_gamma_adjustments(max_age_minutes)
    
    def _read_gamma_adjustments(self, max_age_minutes=5) -> Optional[Dict]:
        """Read gamma adjustments from MLOptionTrading output"""
        
        if not self.ml_option_path:
            logger.debug("ML Option Trading path not configured")
            return None
            
        adj_file = Path(self.ml_option_path) / 'data' / 'gamma_adjustments.json'
        
        if not adj_file.exists():
            logger.debug(f"Gamma adjustments file not found: {adj_file}")
            return None
        
        try:
            with open(adj_file, 'r') as f:
                data = json.load(f)
            
            # Check freshness
            timestamp = datetime.fromisoformat(data.get('timestamp', ''))
            age = datetime.now() - timestamp
            
            if age > timedelta(minutes=max_age_minutes):
                logger.debug(f"Gamma data too old: {age}")
                return None
                
            logger.info(f"Loaded gamma adjustments (age: {age.seconds}s)")
            return data
            
        except Exception as e:
            logger.error(f"Error reading gamma adjustments: {e}")
            return None
    
    def calculate_strategy_adjustments(self, strategy_type: str, gamma_data: Dict) -> int:
        """
        Calculate strategy-specific adjustments from gamma data
        
        Args:
            strategy_type: Type of strategy (Butterfly, Iron_Condor, Vertical)
            gamma_data: Gamma analysis data
            
        Returns:
            Score adjustment value
        """
        if not gamma_data:
            return 0
        
        # Get base adjustments
        adjustments = gamma_data.get('score_adjustments', {})
        strategy_adj = adjustments.get(strategy_type, 0)
        
        # Apply signal strength multiplier if available
        signals = gamma_data.get('signals', {})
        if signals.get('signal_strength') == 'strong':
            strategy_adj = int(strategy_adj * 1.5)
        
        # Cap adjustments to reasonable range
        strategy_adj = max(-20, min(20, strategy_adj))
        
        logger.debug(f"{strategy_type} gamma adjustment: {strategy_adj}")
        return strategy_adj
    
    def get_gamma_metrics(self, gamma_data: Dict) -> Dict:
        """
        Extract key gamma metrics for display/logging
        
        Args:
            gamma_data: Gamma analysis data
            
        Returns:
            Dictionary with formatted metrics
        """
        if not gamma_data:
            return {}
        
        metrics = gamma_data.get('gamma_metrics', {})
        signals = gamma_data.get('signals', {})
        
        return {
            'net_gex': metrics.get('net_gex', 0),
            'gamma_flip': metrics.get('gamma_flip', 0),
            'call_wall': metrics.get('call_wall', 0),
            'put_wall': metrics.get('put_wall', 0),
            'regime': signals.get('gamma_regime', 'unknown'),
            'bias': signals.get('bias', 'neutral'),
            'confidence': signals.get('confidence', 'low')
        }
    
    def format_gamma_summary(self, gamma_data: Dict) -> str:
        """
        Format gamma data into a human-readable summary
        
        Args:
            gamma_data: Gamma analysis data
            
        Returns:
            Formatted string summary
        """
        if not gamma_data:
            return "No gamma data available"
        
        metrics = self.get_gamma_metrics(gamma_data)
        
        return (
            f"Gamma Analysis Summary:\n"
            f"  Net GEX: ${metrics['net_gex']:,.0f}\n"
            f"  Regime: {metrics['regime'].upper()}\n"
            f"  Gamma Flip: {metrics['gamma_flip']:.0f}\n"
            f"  Call Wall: {metrics['call_wall']:.0f}\n"
            f"  Put Wall: {metrics['put_wall']:.0f}\n"
            f"  Trading Bias: {metrics['bias'].replace('_', ' ').title()}\n"
            f"  Confidence: {metrics['confidence'].upper()}"
        )


# Example usage and testing
if __name__ == "__main__":
    # Test the wrapper
    wrapper = EnhancedGEXWrapper(mode='file')
    
    # Try to get gamma adjustments
    gamma_data = wrapper.get_gamma_adjustments()
    
    if gamma_data:
        print("Successfully loaded gamma data!")
        print(wrapper.format_gamma_summary(gamma_data))
        
        # Test strategy adjustments
        for strategy in ['Butterfly', 'Iron_Condor', 'Vertical']:
            adj = wrapper.calculate_strategy_adjustments(strategy, gamma_data)
            print(f"{strategy} adjustment: {adj}")
    else:
        print("No gamma data available - ensure MLOptionTrading is running")
