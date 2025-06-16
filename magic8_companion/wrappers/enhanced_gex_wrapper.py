"""
Enhanced GEX Wrapper for Magic8-Companion
Integrates with MLOptionTrading's gamma analysis for real-time scoring adjustments
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EnhancedGEXWrapper:
    """
    Wrapper that reads gamma analysis from MLOptionTrading
    and provides scoring adjustments to Magic8-Companion
    """
    
    def __init__(self):
        """Initialize the enhanced GEX wrapper"""
        # Find MLOptionTrading data directory
        self.ml_option_trading_path = self._find_mloptiontrading_path()
        self.gamma_data_file = self.ml_option_trading_path / "data" / "gamma_adjustments.json"
        self.full_gamma_file = self.ml_option_trading_path / "data" / "gamma_analysis.json"
        
        # Cache settings
        self.cache_duration_minutes = 5
        self.last_data = None
        self.last_read_time = None
        
        logger.info(f"Enhanced GEX wrapper initialized with path: {self.ml_option_trading_path}")
    
    def _find_mloptiontrading_path(self) -> Path:
        """Find MLOptionTrading installation path"""
        import os
        
        # Try environment variable first
        if env_path := os.environ.get('MLOPTIONTRADING_PATH'):
            return Path(env_path)
        
        # Try common relative paths
        possible_paths = [
            Path("../MLOptionTrading"),  # Side by side
            Path.home() / "magic8" / "MLOptionTrading",  # Standard location
            Path(__file__).parent.parent.parent.parent / "MLOptionTrading"  # Relative
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "gamma_scheduler.py").exists():
                logger.info(f"Found MLOptionTrading at: {path}")
                return path
        
        # Default path
        default = Path.home() / "magic8" / "MLOptionTrading"
        logger.warning(f"MLOptionTrading not found, using default: {default}")
        return default
    
    def get_gamma_adjustments(self) -> Optional[Dict]:
        """Get the latest gamma adjustments from MLOptionTrading"""
        try:
            # Check cache
            if self.last_data and self.last_read_time:
                age = datetime.now() - self.last_read_time
                if age < timedelta(minutes=self.cache_duration_minutes):
                    logger.debug("Using cached gamma data")
                    return self.last_data
            
            # Read fresh data
            if self.gamma_data_file.exists():
                with open(self.gamma_data_file, 'r') as f:
                    data = json.load(f)
                
                # Check data freshness
                timestamp = datetime.fromisoformat(data['timestamp'])
                age = datetime.now() - timestamp
                
                if age < timedelta(minutes=30):  # Data is fresh enough
                    self.last_data = data
                    self.last_read_time = datetime.now()
                    logger.debug(f"Loaded gamma data from {age.total_seconds()/60:.1f} minutes ago")
                    return data
                else:
                    logger.warning(f"Gamma data is {age.total_seconds()/60:.0f} minutes old")
                    return None
            else:
                logger.debug("No gamma adjustments file found")
                return None
                
        except Exception as e:
            logger.error(f"Error reading gamma adjustments: {e}")
            return None
    
    def calculate_strategy_adjustments(self, strategy: str, gamma_data: Dict) -> float:
        """Calculate scoring adjustments for a specific strategy"""
        if not gamma_data or 'score_adjustments' not in gamma_data:
            return 0.0
        
        adjustments = gamma_data.get('score_adjustments', {})
        base_adjustment = adjustments.get(strategy, 0)
        
        # Apply confidence scaling if available
        if 'confidence' in gamma_data:
            confidence = gamma_data['confidence']
            if confidence == 'strong':
                base_adjustment *= 1.2
            elif confidence == 'weak':
                base_adjustment *= 0.8
        
        # Cap adjustments at ±20 points
        return max(-20, min(20, base_adjustment))
    
    def get_gamma_metrics(self, gamma_data: Dict) -> Dict:
        """Extract key gamma metrics for logging"""
        if not gamma_data:
            return {
                'regime': 'unknown',
                'bias': 'neutral',
                'net_gex': 0,
                'confidence': 'none'
            }
        
        # Try to get from the full analysis file for more details
        try:
            if self.full_gamma_file.exists():
                with open(self.full_gamma_file, 'r') as f:
                    full_data = json.load(f)
                    
                return {
                    'regime': full_data.get('signals', {}).get('gamma_regime', 'unknown'),
                    'bias': full_data.get('signals', {}).get('bias', 'neutral'),
                    'net_gex': full_data.get('gamma_metrics', {}).get('net_gex', 0),
                    'confidence': full_data.get('signals', {}).get('confidence', 'medium'),
                    'spot_price': full_data.get('spot_price', 0),
                    'gamma_flip': full_data.get('gamma_metrics', {}).get('gamma_flip', 0),
                    'call_wall': full_data.get('gamma_metrics', {}).get('call_wall', 0),
                    'put_wall': full_data.get('gamma_metrics', {}).get('put_wall', 0)
                }
        except Exception as e:
            logger.debug(f"Could not read full gamma data: {e}")
        
        # Fallback to basic data
        return {
            'regime': gamma_data.get('gamma_regime', 'unknown'),
            'bias': 'neutral',
            'net_gex': 0,
            'confidence': 'medium'
        }
    
    def get_key_levels(self) -> Optional[Dict]:
        """Get key gamma levels (walls, flip point)"""
        gamma_data = self.get_gamma_adjustments()
        if not gamma_data or 'key_levels' not in gamma_data:
            return None
        
        return gamma_data['key_levels']
    
    def is_gamma_analysis_available(self) -> bool:
        """Check if gamma analysis is available and running"""
        # Check if MLOptionTrading is installed
        if not self.ml_option_trading_path.exists():
            return False
        
        # Check if gamma data exists and is recent
        if self.gamma_data_file.exists():
            try:
                with open(self.gamma_data_file, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                age = datetime.now() - timestamp
                return age < timedelta(hours=1)  # Consider available if updated within an hour
            except:
                pass
        
        return False
    
    def get_status(self) -> Dict:
        """Get status of gamma analysis integration"""
        status = {
            'available': self.is_gamma_analysis_available(),
            'mloptiontrading_path': str(self.ml_option_trading_path),
            'data_file_exists': self.gamma_data_file.exists(),
            'last_update': None,
            'data_age_minutes': None
        }
        
        if self.gamma_data_file.exists():
            try:
                with open(self.gamma_data_file, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                status['last_update'] = data['timestamp']
                status['data_age_minutes'] = (datetime.now() - timestamp).total_seconds() / 60
            except:
                pass
        
        return status
