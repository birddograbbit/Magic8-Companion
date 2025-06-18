"""
Enhanced GEX Wrapper for Magic8-Companion
Now uses integrated gamma analysis instead of external files
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

from magic8_companion.analysis.gamma.gamma_runner import run_gamma_analysis

logger = logging.getLogger(__name__)


class EnhancedGEXWrapper:
    """
    Wrapper that provides gamma analysis scoring adjustments to Magic8-Companion
    Now uses integrated gamma analysis instead of reading from MLOptionTrading
    """
    
    def __init__(self):
        """Initialize the enhanced GEX wrapper"""
        # Use the integrated native gamma analysis
        
        # Cache settings
        self.cache_duration_minutes = 5
        self.last_analysis = None
        self.last_analysis_time = None
        
        # Backwards compatibility - check for external files
        self.external_mode = False
        self._check_external_mode()
        
        logger.info("Enhanced GEX wrapper initialized with integrated gamma analysis")
    
    def _check_external_mode(self):
        """Check if we should use external MLOptionTrading files for backwards compatibility"""
        import os
        
        # Check if MLOptionTrading path is configured
        if ml_path := os.environ.get('M8C_ML_OPTION_TRADING_PATH'):
            ml_path = Path(ml_path)
            if ml_path.exists() and (ml_path / "data" / "gamma_adjustments.json").exists():
                self.external_mode = True
                self.ml_option_trading_path = ml_path
                self.gamma_data_file = ml_path / "data" / "gamma_adjustments.json"
                self.full_gamma_file = ml_path / "data" / "gamma_analysis.json"
                logger.info("External MLOptionTrading files detected - using compatibility mode")
    
    def get_gamma_adjustments(self, symbol: str = 'SPX') -> Optional[Dict]:
        """
        Get the latest gamma adjustments
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Gamma adjustments dictionary
        """
        try:
            # Check cache
            if self.last_analysis and self.last_analysis_time:
                age = datetime.now() - self.last_analysis_time
                if age < timedelta(minutes=self.cache_duration_minutes):
                    logger.debug("Using cached gamma analysis")
                    return self.last_analysis
            
            # If in external mode, try reading files first
            if self.external_mode:
                external_data = self._read_external_data()
                if external_data:
                    return external_data
            
            # Run integrated gamma analysis using native implementation
            logger.info(f"Running gamma analysis for {symbol}")
            analysis = run_gamma_analysis(symbol, save_results=False)

            if analysis:
                formatted = self._format_native_analysis(analysis)
                self.last_analysis = formatted
                self.last_analysis_time = datetime.now()
                return formatted
            else:
                logger.warning("Gamma analysis failed")
                return None
                
        except Exception as e:
            logger.error(f"Error getting gamma adjustments: {e}")
            return None
    
    def _read_external_data(self) -> Optional[Dict]:
        """Read gamma data from external MLOptionTrading files"""
        try:
            if self.gamma_data_file.exists():
                with open(self.gamma_data_file, 'r') as f:
                    data = json.load(f)
                
                # Check data freshness
                timestamp = datetime.fromisoformat(data['timestamp'])
                age = datetime.now() - timestamp
                
                if age < timedelta(minutes=30):
                    # Convert to internal format
                    return {
                        'symbol': data.get('symbol', 'SPX'),
                        'timestamp': data['timestamp'],
                        'score_adjustments': data.get('score_adjustments', {}),
                        'signals': {
                            'gamma_regime': data.get('gamma_regime', 'unknown'),
                            'bias': data.get('market_bias', 'neutral')
                        },
                        'gamma_metrics': {
                            'gamma_flip': data.get('key_levels', {}).get('gamma_flip', 0),
                            'call_wall': data.get('key_levels', {}).get('call_wall', 0),
                            'put_wall': data.get('key_levels', {}).get('put_wall', 0)
                        }
                    }
                else:
                    logger.warning(f"External gamma data is {age.total_seconds()/60:.0f} minutes old")
        except Exception as e:
            logger.debug(f"Could not read external gamma data: {e}")
        
        return None

    def _format_native_analysis(self, analysis: Dict) -> Dict:
        """Format native gamma analysis for compatibility."""
        levels = analysis.get('levels', {})
        regime = analysis.get('regime_analysis', {})

        return {
            'symbol': analysis.get('symbol'),
            'timestamp': analysis.get('analysis_timestamp'),
            'score_adjustments': {},
            'signals': {
                'gamma_regime': regime.get('regime', 'unknown'),
                'bias': regime.get('bias', 'neutral'),
                'confidence': regime.get('confidence', 'medium'),
            },
            'gamma_metrics': {
                'net_gex': analysis.get('net_gex', 0),
                'gamma_flip': levels.get('zero_gamma', 0),
                'call_wall': levels.get('call_wall', 0),
                'put_wall': levels.get('put_wall', 0),
                'spot_price': analysis.get('spot_price', 0),
            },
            'spot_price': analysis.get('spot_price', 0),
        }
    
    def calculate_strategy_adjustments(self, strategy: str, gamma_data: Dict) -> float:
        """
        Calculate scoring adjustments for a specific strategy
        
        Args:
            strategy: Strategy name
            gamma_data: Gamma analysis data
            
        Returns:
            Score adjustment value
        """
        if not gamma_data or 'score_adjustments' not in gamma_data:
            return 0.0
        
        adjustments = gamma_data.get('score_adjustments', {})
        base_adjustment = adjustments.get(strategy, 0)
        
        # Apply confidence scaling if available
        signals = gamma_data.get('signals', {})
        if 'confidence' in signals:
            confidence = signals['confidence']
            if confidence == 'high':
                base_adjustment *= 1.2
            elif confidence == 'low':
                base_adjustment *= 0.8
        
        # Cap adjustments at ±20 points
        return max(-20, min(20, base_adjustment))
    
    def get_gamma_metrics(self, gamma_data: Dict) -> Dict:
        """
        Extract key gamma metrics for logging
        
        Args:
            gamma_data: Gamma analysis data
            
        Returns:
            Gamma metrics dictionary
        """
        if not gamma_data:
            return {
                'regime': 'unknown',
                'bias': 'neutral',
                'net_gex': 0,
                'confidence': 'none'
            }
        
        signals = gamma_data.get('signals', {})
        metrics = gamma_data.get('gamma_metrics', {})
        
        return {
            'regime': signals.get('gamma_regime', 'unknown'),
            'bias': signals.get('bias', 'neutral'),
            'net_gex': metrics.get('net_gex', 0),
            'confidence': signals.get('confidence', 'medium'),
            'spot_price': gamma_data.get('spot_price', 0),
            'gamma_flip': metrics.get('gamma_flip', 0),
            'call_wall': metrics.get('call_wall', 0),
            'put_wall': metrics.get('put_wall', 0)
        }
    
    def get_key_levels(self, symbol: str = 'SPX') -> Optional[Dict]:
        """
        Get key gamma levels (walls, flip point)
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Key levels dictionary
        """
        gamma_data = self.get_gamma_adjustments(symbol)
        if not gamma_data:
            return None
        
        metrics = gamma_data.get('gamma_metrics', {})
        return {
            'gamma_flip': metrics.get('gamma_flip', 0),
            'call_wall': metrics.get('call_wall', 0),
            'put_wall': metrics.get('put_wall', 0)
        }
    
    def is_gamma_analysis_available(self) -> bool:
        """Check if gamma analysis is available"""
        try:
            if self.last_analysis_time:
                age = datetime.now() - self.last_analysis_time
                return age < timedelta(hours=1)
            return False
        except Exception:
            return False
    
    def get_status(self) -> Dict:
        """Get status of gamma analysis integration"""
        status = {
            'available': self.is_gamma_analysis_available(),
            'mode': 'external' if self.external_mode else 'integrated',
            'last_update': None,
            'data_age_minutes': None
        }
        
        # Get latest analysis info
        try:
            if self.external_mode and self.gamma_data_file.exists():
                with open(self.gamma_data_file, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                status['last_update'] = data['timestamp']
                status['data_age_minutes'] = (datetime.now() - timestamp).total_seconds() / 60
            else:
                if self.last_analysis_time and self.last_analysis:
                    timestamp = self.last_analysis_time
                    status['last_update'] = self.last_analysis.get('timestamp')
                    status['data_age_minutes'] = (datetime.now() - timestamp).total_seconds() / 60
        except:
            pass
        
        return status
