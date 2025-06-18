"""
Market Regime Analyzer for Magic8-Companion.
Determines market regime and trading bias from GEX data.
"""
from typing import Dict, Optional, List, Tuple
import logging
from datetime import datetime
from ...unified_config import settings

logger = logging.getLogger(__name__)


class MarketRegimeAnalyzer:
    """Determine market regime and trading bias from GEX."""
    
    def __init__(self):
        """Initialize with regime thresholds from settings."""
        self.regime_thresholds = settings.gamma_regime_thresholds
        
    def analyze_regime(self, gex_data: Dict, spot_price: float) -> Dict:
        """
        Comprehensive regime analysis.
        
        Args:
            gex_data: GEX calculation results
            spot_price: Current spot price
            
        Returns:
            Dict with regime analysis
        """
        net_gex = gex_data.get('net_gex', 0)
        levels = gex_data.get('levels', {})
        
        # Basic regime determination
        regime = self._determine_regime(net_gex)
        
        # Magnitude analysis
        magnitude = self._analyze_magnitude(net_gex)
        
        # Position relative to levels
        bias = self._analyze_bias(spot_price, levels, regime)
        
        # Expected market behavior
        behavior = self._expected_behavior(regime, magnitude, bias)
        
        # Trading recommendations
        recommendations = self._get_trading_recommendations(
            regime, magnitude, bias, levels
        )
        
        # Risk assessment
        risk_metrics = self._assess_risk(gex_data, spot_price, levels)
        
        return {
            'regime': regime,
            'magnitude': magnitude,
            'bias': bias,
            'net_gex_billions': net_gex / 1e9,
            'expected_behavior': behavior,
            'recommendations': recommendations,
            'risk_metrics': risk_metrics,
            'confidence': self._calculate_confidence(gex_data, magnitude)
        }
    
    def _determine_regime(self, net_gex: float) -> str:
        """Determine basic regime from net GEX."""
        if abs(net_gex) < 1e6:  # Less than $1M
            return 'neutral'
        elif net_gex > 0:
            return 'positive'
        else:
            return 'negative'
    
    def _analyze_magnitude(self, net_gex: float) -> str:
        """Analyze GEX magnitude."""
        abs_gex = abs(net_gex)
        
        if abs_gex >= self.regime_thresholds['extreme']:
            return 'extreme'
        elif abs_gex >= self.regime_thresholds['high']:
            return 'high'
        elif abs_gex >= self.regime_thresholds['moderate']:
            return 'moderate'
        else:
            return 'low'
    
    def _analyze_bias(self, spot_price: float, levels: Dict, regime: str) -> str:
        """Analyze directional bias based on spot position."""
        call_wall = levels.get('call_wall')
        put_wall = levels.get('put_wall')
        zero_gamma = levels.get('zero_gamma')
        
        if not call_wall or not put_wall:
            return 'neutral'
        
        # Calculate position within range
        range_size = call_wall - put_wall
        if range_size <= 0:
            return 'neutral'
        
        position = (spot_price - put_wall) / range_size
        
        # Determine bias based on position and regime
        if regime == 'positive':
            # In positive gamma, extremes get pushed back
            if position < 0.2:
                return 'support_test'
            elif position > 0.8:
                return 'resistance_test'
            else:
                return 'range_bound'
        else:  # negative regime
            # In negative gamma, moves get exacerbated
            if position < 0.3:
                return 'bearish'
            elif position > 0.7:
                return 'bullish'
            else:
                return 'volatile'
    
    def _expected_behavior(self, regime: str, magnitude: str, bias: str) -> Dict:
        """Determine expected market behavior."""
        behaviors = {
            'positive': {
                'description': 'Range-bound, mean-reverting',
                'volatility': 'Low to moderate',
                'trend_strength': 'Weak',
                'reversal_probability': 'High at extremes'
            },
            'negative': {
                'description': 'Trending, volatile',
                'volatility': 'High',
                'trend_strength': 'Strong',
                'reversal_probability': 'Low'
            },
            'neutral': {
                'description': 'Uncertain, transitional',
                'volatility': 'Variable',
                'trend_strength': 'Variable',
                'reversal_probability': 'Moderate'
            }
        }
        
        behavior = behaviors.get(regime, behaviors['neutral']).copy()
        
        # Adjust for magnitude
        if magnitude == 'extreme':
            behavior['volatility'] = 'Suppressed' if regime == 'positive' else 'Extreme'
            behavior['caution'] = 'High - extreme positioning'
        elif magnitude == 'low':
            behavior['volatility'] = 'Potentially increasing'
            behavior['caution'] = 'Watch for regime change'
        
        # Adjust for bias
        behavior['directional_bias'] = bias
        
        return behavior
    
    def _get_trading_recommendations(self, regime: str, magnitude: str, 
                                   bias: str, levels: Dict) -> List[Dict]:
        """Generate trading recommendations based on regime."""
        recommendations = []
        
        # Strategy recommendations
        if regime == 'positive':
            recommendations.append({
                'strategy': 'Iron Condor',
                'rationale': 'Range-bound market favors premium selling',
                'confidence': 'high' if magnitude in ['moderate', 'high'] else 'moderate'
            })
            recommendations.append({
                'strategy': 'Butterfly',
                'rationale': 'Low volatility environment',
                'confidence': 'moderate'
            })
            
            if bias in ['support_test', 'resistance_test']:
                recommendations.append({
                    'strategy': 'Vertical Spread',
                    'rationale': f'Test of {bias.split("_")[0]} level',
                    'direction': 'bullish' if bias == 'support_test' else 'bearish',
                    'confidence': 'moderate'
                })
        
        elif regime == 'negative':
            recommendations.append({
                'strategy': 'Vertical Spread',
                'rationale': 'Trending market favors directional plays',
                'direction': 'follow_trend',
                'confidence': 'high' if magnitude in ['moderate', 'high'] else 'moderate'
            })
            
            if magnitude != 'extreme':
                recommendations.append({
                    'strategy': 'Long Straddle/Strangle',
                    'rationale': 'High volatility environment',
                    'confidence': 'moderate'
                })
        
        # Risk management
        if magnitude == 'extreme':
            recommendations.append({
                'action': 'Reduce Position Size',
                'rationale': 'Extreme positioning increases reversal risk',
                'confidence': 'high'
            })
        
        # Level-based recommendations
        if levels.get('call_wall') and levels.get('put_wall'):
            recommendations.append({
                'levels': {
                    'resistance': levels['call_wall'],
                    'support': levels['put_wall'],
                    'pivot': levels.get('zero_gamma')
                },
                'action': 'Use levels for entry/exit',
                'confidence': 'high'
            })
        
        return recommendations
    
    def _assess_risk(self, gex_data: Dict, spot_price: float, levels: Dict) -> Dict:
        """Assess current market risks."""
        risks = {
            'gamma_flip_risk': 'low',
            'volatility_expansion_risk': 'low',
            'gap_risk': 'low',
            'liquidity_risk': 'low'
        }
        
        # Gamma flip risk
        zero_gamma = levels.get('zero_gamma')
        if zero_gamma:
            distance_to_flip = abs(spot_price - zero_gamma) / spot_price
            if distance_to_flip < 0.01:  # Within 1%
                risks['gamma_flip_risk'] = 'high'
            elif distance_to_flip < 0.02:  # Within 2%
                risks['gamma_flip_risk'] = 'moderate'
        
        # Volatility expansion risk
        net_gex = gex_data.get('net_gex', 0)
        if net_gex < 0:
            risks['volatility_expansion_risk'] = 'high'
        elif abs(net_gex) < self.regime_thresholds['moderate']:
            risks['volatility_expansion_risk'] = 'moderate'
        
        # Gap risk
        concentration = gex_data.get('gex_concentration', 0)
        if concentration > 0.5:  # High concentration
            risks['gap_risk'] = 'moderate'
            if gex_data.get('regime') == 'negative':
                risks['gap_risk'] = 'high'
        
        # Liquidity risk
        flip_zone = levels.get('flip_zone', {})
        if flip_zone.get('spot_in_zone'):
            risks['liquidity_risk'] = 'moderate'
        
        return risks
    
    def _calculate_confidence(self, gex_data: Dict, magnitude: str) -> float:
        """Calculate confidence in regime analysis."""
        confidence = 0.5  # Base confidence
        
        # Higher magnitude = higher confidence
        magnitude_scores = {
            'extreme': 0.3,
            'high': 0.2,
            'moderate': 0.1,
            'low': 0.0
        }
        confidence += magnitude_scores.get(magnitude, 0)
        
        # More data points = higher confidence
        strike_count = len(gex_data.get('strike_gex', {}))
        if strike_count > 50:
            confidence += 0.1
        elif strike_count > 20:
            confidence += 0.05
        
        # Clear levels = higher confidence
        levels = gex_data.get('levels', {})
        if levels.get('call_wall') and levels.get('put_wall'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def compare_regimes(self, current: Dict, previous: Dict) -> Dict:
        """Compare current regime with previous."""
        if not previous:
            return {'changed': False}
        
        changes = {
            'regime_changed': current['regime'] != previous.get('regime'),
            'magnitude_changed': current['magnitude'] != previous.get('magnitude'),
            'bias_changed': current['bias'] != previous.get('bias'),
            'previous_regime': previous.get('regime'),
            'current_regime': current['regime'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Determine significance
        changes['significant'] = (
            changes['regime_changed'] or 
            (changes['magnitude_changed'] and 
             current['magnitude'] in ['extreme', 'high'])
        )
        
        return changes
