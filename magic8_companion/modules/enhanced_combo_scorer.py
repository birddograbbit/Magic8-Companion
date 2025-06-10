"""
Enhanced Combo Scorer Module
Integrates all enhanced indicators while maintaining backward compatibility.
Ship-fast approach: Wrapper around existing scorer with optional enhancements.
"""

import os
import logging
from typing import Dict, Optional, List
from magic8_companion.modules.combo_scorer_simplified import ComboScorer
from magic8_companion.wrappers import GreeksWrapper, GammaExposureWrapper, VolumeOIWrapper

logger = logging.getLogger(__name__)


class EnhancedComboScorer(ComboScorer):
    """
    Enhanced version of ComboScorer with additional indicators.
    
    Maintains full backward compatibility - enhancements are optional.
    """
    
    def __init__(self):
        """Initialize enhanced scorer with optional components."""
        super().__init__()
        
        # Check if enhancements are enabled
        self.enable_greeks = os.getenv('ENABLE_GREEKS', 'false').lower() == 'true'
        self.enable_advanced_gex = os.getenv('ENABLE_ADVANCED_GEX', 'false').lower() == 'true'
        self.enable_volume_analysis = os.getenv('ENABLE_VOLUME_ANALYSIS', 'false').lower() == 'true'
        
        # Initialize wrappers if enabled
        if self.enable_greeks:
            self.greeks_wrapper = GreeksWrapper()
            logger.info("Greeks calculations enabled")
            
        if self.enable_advanced_gex:
            self.gex_wrapper = GammaExposureWrapper()
            logger.info("Advanced GEX calculations enabled")
            
        if self.enable_volume_analysis:
            self.volume_wrapper = VolumeOIWrapper()
            logger.info("Volume/OI analysis enabled")
    
    def calculate_strategy_score(
        self,
        strategy_type: str,
        market_conditions: Dict
    ) -> Dict:
        """
        Calculate enhanced strategy score with optional indicators.
        
        Fully backward compatible - works with original 3 indicators only.
        """
        # Get base score from parent class
        base_result = super().calculate_strategy_score(strategy_type, market_conditions)
        
        # If no enhancements enabled, return base result
        if not any([self.enable_greeks, self.enable_advanced_gex, self.enable_volume_analysis]):
            return base_result
        
        # Start with base score
        enhanced_score = base_result['score']
        score_components = {
            'base_score': base_result['score'],
            'base_components': base_result.get('components', {})
        }
        
        # Add Greeks adjustments if enabled
        if self.enable_greeks and 'option_chain' in market_conditions:
            try:
                greeks_adj = self._calculate_greeks_adjustments(
                    strategy_type, market_conditions
                )
                enhanced_score += sum(greeks_adj.values())
                score_components['greeks_adjustments'] = greeks_adj
            except Exception as e:
                logger.warning(f"Greeks calculation failed: {e}")
        
        # Add advanced GEX adjustments if enabled
        if self.enable_advanced_gex and 'option_chain' in market_conditions:
            try:
                gex_adj = self._calculate_gex_adjustments(
                    strategy_type, market_conditions
                )
                enhanced_score += sum(gex_adj.values())
                score_components['gex_adjustments'] = gex_adj
            except Exception as e:
                logger.warning(f"GEX calculation failed: {e}")
        
        # Add volume/OI adjustments if enabled
        if self.enable_volume_analysis and 'option_chain' in market_conditions:
            try:
                volume_adj = self._calculate_volume_adjustments(
                    strategy_type, market_conditions
                )
                enhanced_score += sum(volume_adj.values())
                score_components['volume_adjustments'] = volume_adj
            except Exception as e:
                logger.warning(f"Volume analysis failed: {e}")
        
        # Ensure score stays in valid range
        enhanced_score = max(0, min(100, enhanced_score))
        
        # Determine confidence based on enhanced score
        if enhanced_score >= 75:
            confidence = "HIGH"
        elif enhanced_score >= 50:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return {
            'score': enhanced_score,
            'confidence': confidence,
            'should_trade': enhanced_score >= self.min_score,
            'components': score_components,
            'enhanced': True
        }
    
    def _calculate_greeks_adjustments(
        self,
        strategy_type: str,
        market_conditions: Dict
    ) -> Dict[str, float]:
        """Calculate adjustments based on Greeks."""
        # Extract necessary data
        spot = market_conditions.get('spot_price', 5850)
        option_chain = market_conditions.get('option_chain', [])
        
        if not option_chain:
            return {}
        
        # Get ATM strike for Greeks calculation
        strikes = [opt['strike'] for opt in option_chain if 'strike' in opt]
        if not strikes:
            return {}
            
        atm_strike = min(strikes, key=lambda x: abs(x - spot))
        
        # Find ATM option data
        atm_option = next((opt for opt in option_chain if opt.get('strike') == atm_strike), None)
        if not atm_option:
            return {}
        
        # Calculate Greeks for ATM option
        iv = atm_option.get('implied_volatility', 0.15)
        time_to_exp = market_conditions.get('time_to_expiry', 1/365)
        
        greeks = self.greeks_wrapper.calculate_single_cached(
            spot, atm_strike, time_to_exp, iv, 'c'
        )
        
        # Get strategy-specific adjustments
        return self.greeks_wrapper.get_strategy_greeks_adjustments(
            strategy_type, greeks
        )
    
    def _calculate_gex_adjustments(
        self,
        strategy_type: str,
        market_conditions: Dict
    ) -> Dict[str, float]:
        """Calculate adjustments based on advanced GEX."""
        option_chain = market_conditions.get('option_chain', [])
        spot = market_conditions.get('spot_price', 5850)
        
        if not option_chain:
            return {}
        
        # Calculate GEX
        gex_data = self.gex_wrapper.calculate_net_gex(
            option_chain, spot, is_zero_dte=True
        )
        
        # Get strategy-specific adjustments
        return self.gex_wrapper.get_strategy_gex_adjustments(
            strategy_type, gex_data, spot
        )
    
    def _calculate_volume_adjustments(
        self,
        strategy_type: str,
        market_conditions: Dict
    ) -> Dict[str, float]:
        """Calculate adjustments based on volume/OI analysis."""
        option_chain = market_conditions.get('option_chain', [])
        
        if not option_chain:
            return {}
        
        # Analyze volume/OI
        volume_data = self.volume_wrapper.analyze(option_chain)
        
        # Get strategy-specific adjustments
        return self.volume_wrapper.get_strategy_volume_adjustments(
            strategy_type, volume_data
        )
    
    def score_all_strategies(
        self,
        market_conditions: Dict
    ) -> Dict[str, Dict]:
        """
        Score all strategies with enhanced indicators.
        
        Maintains same output format as base class.
        """
        results = {}
        
        for strategy in self.strategy_weights.keys():
            results[strategy] = self.calculate_strategy_score(
                strategy, market_conditions
            )
        
        return results
    
    def get_enhancement_status(self) -> Dict[str, bool]:
        """Return status of which enhancements are enabled."""
        return {
            'greeks_enabled': self.enable_greeks,
            'advanced_gex_enabled': self.enable_advanced_gex,
            'volume_analysis_enabled': self.enable_volume_analysis
        }


# Example usage and testing
if __name__ == "__main__":
    # Test with mock data
    import os
    
    # Enable all enhancements for testing
    os.environ['ENABLE_GREEKS'] = 'true'
    os.environ['ENABLE_ADVANCED_GEX'] = 'true'
    os.environ['ENABLE_VOLUME_ANALYSIS'] = 'true'
    
    scorer = EnhancedComboScorer()
    
    # Mock market conditions with option chain
    market_conditions = {
        'iv_rank': 45,
        'range_expectation': 0.015,
        'gamma_environment': 'Neutral',
        'spot_price': 5850,
        'time_to_expiry': 1/365,
        'option_chain': [
            {
                'strike': 5800,
                'implied_volatility': 0.14,
                'call_gamma': 0.0012,
                'put_gamma': 0.0008,
                'call_open_interest': 5000,
                'put_open_interest': 3000,
                'call_volume': 2500,
                'put_volume': 1800
            },
            {
                'strike': 5850,
                'implied_volatility': 0.15,
                'call_gamma': 0.0018,
                'put_gamma': 0.0015,
                'call_open_interest': 8000,
                'put_open_interest': 6000,
                'call_volume': 12000,
                'put_volume': 8000
            },
            {
                'strike': 5900,
                'implied_volatility': 0.16,
                'call_gamma': 0.0010,
                'put_gamma': 0.0020,
                'call_open_interest': 4000,
                'put_open_interest': 7000,
                'call_volume': 1000,
                'put_volume': 3500
            }
        ]
    }
    
    print("Enhanced Combo Scorer Test")
    print(f"Enhancement Status: {scorer.get_enhancement_status()}")
    print("\nScoring all strategies with enhanced indicators:")
    
    results = scorer.score_all_strategies(market_conditions)
    
    for strategy, result in results.items():
        print(f"\n{strategy}:")
        print(f"  Score: {result['score']:.1f}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Should Trade: {result['should_trade']}")
        if 'components' in result:
            print(f"  Components: {result['components']}")
