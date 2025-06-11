"""
Volume/Open Interest Wrapper Module
Analyzes volume and open interest patterns for market sentiment.
Ship-fast approach: Simple ratios and anomaly detection.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class VolumeOIWrapper:
    """
    Wrapper for Volume and Open Interest analysis.
    
    Key metrics:
    - Volume/OI ratio: Indicates speculation vs hedging
    - Put/Call ratios: Market sentiment
    - Unusual activity: Anomaly detection
    - Strike concentration: Liquidity analysis
    """
    
    def __init__(
        self,
        unusual_threshold: float = 3.0,
        min_oi_filter: int = 100
    ):
        """
        Initialize Volume/OI analyzer.
        
        Args:
            unusual_threshold: Multiplier for unusual activity detection
            min_oi_filter: Minimum OI to consider (filters noise)
        """
        self.unusual_threshold = unusual_threshold
        self.min_oi_filter = min_oi_filter
        
    def analyze(
        self,
        option_chain: List[Dict],
        historical_avg: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Analyze volume and open interest patterns.
        
        Args:
            option_chain: List of option data dictionaries
            historical_avg: Optional historical averages for comparison
            
        Returns:
            Dictionary with volume/OI metrics
        """
        try:
            # Filter low OI options
            filtered_chain = self._filter_low_oi(option_chain)
            
            if not filtered_chain:
                return self._empty_volume_result()
            
            # Calculate primary metrics
            vol_oi_ratio = self._calculate_volume_oi_ratio(filtered_chain)
            pc_volume = self._calculate_put_call_volume(filtered_chain)
            pc_oi = self._calculate_put_call_oi(filtered_chain)
            
            # Analyze concentration
            strike_concentration = self._analyze_strike_concentration(filtered_chain)
            
            # Detect unusual activity
            unusual_strikes = self._detect_unusual_activity(
                filtered_chain, historical_avg
            )
            
            # Calculate liquidity score
            liquidity_score = self._calculate_liquidity_score(filtered_chain)
            
            # Determine market sentiment
            sentiment = self._determine_sentiment(vol_oi_ratio, pc_volume)
            
            return {
                'volume_oi_ratio': vol_oi_ratio,
                'put_call_volume': pc_volume,
                'put_call_oi': pc_oi,
                'strike_concentration': strike_concentration,
                'unusual_activity_count': len(unusual_strikes),
                'unusual_strikes': unusual_strikes[:5],  # Top 5 unusual
                'liquidity_score': liquidity_score,
                'sentiment': sentiment,
                'total_volume': sum(self._get_total_volume(opt) for opt in filtered_chain),
                'total_oi': sum(self._get_total_oi(opt) for opt in filtered_chain)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume/OI: {e}")
            return self._empty_volume_result()
    
    def _filter_low_oi(self, option_chain: List[Dict]) -> List[Dict]:
        """Filter out options with low open interest."""
        filtered = []
        
        for opt in option_chain:
            total_oi = (opt.get('call_open_interest', 0) + 
                       opt.get('put_open_interest', 0))
            if total_oi >= self.min_oi_filter:
                filtered.append(opt)
                
        return filtered
    
    def _calculate_volume_oi_ratio(self, option_chain: List[Dict]) -> float:
        """
        Calculate overall volume/OI ratio.
        
        > 2.0: Heavy speculation/day trading
        0.5-2.0: Normal activity
        < 0.5: Positioning/hedging activity
        """
        total_volume = 0
        total_oi = 0
        
        for opt in option_chain:
            total_volume += self._get_total_volume(opt)
            total_oi += self._get_total_oi(opt)
        
        if total_oi > 0:
            return total_volume / total_oi
        return 0.0
    
    def _calculate_put_call_volume(self, option_chain: List[Dict]) -> float:
        """Calculate put/call volume ratio."""
        put_volume = sum(opt.get('put_volume', 0) for opt in option_chain)
        call_volume = sum(opt.get('call_volume', 0) for opt in option_chain)
        
        if call_volume > 0:
            return put_volume / call_volume
        return 1.0  # Neutral if no call volume
    
    def _calculate_put_call_oi(self, option_chain: List[Dict]) -> float:
        """Calculate put/call open interest ratio."""
        put_oi = sum(opt.get('put_open_interest', 0) for opt in option_chain)
        call_oi = sum(opt.get('call_open_interest', 0) for opt in option_chain)
        
        if call_oi > 0:
            return put_oi / call_oi
        return 1.0  # Neutral if no call OI
    
    def _analyze_strike_concentration(
        self,
        option_chain: List[Dict]
    ) -> Dict[str, float]:
        """
        Analyze how concentrated volume/OI is across strikes.
        High concentration = liquidity at specific strikes.
        """
        strike_volumes = defaultdict(float)
        strike_ois = defaultdict(float)
        
        for opt in option_chain:
            strike = opt.get('strike', 0)
            strike_volumes[strike] += self._get_total_volume(opt)
            strike_ois[strike] += self._get_total_oi(opt)
        
        # Calculate concentration metrics
        if strike_volumes:
            volume_values = list(strike_volumes.values())
            oi_values = list(strike_ois.values())
            
            # Top 3 strikes concentration
            volume_sorted = sorted(volume_values, reverse=True)
            oi_sorted = sorted(oi_values, reverse=True)
            
            top3_volume_pct = sum(volume_sorted[:3]) / sum(volume_values) if volume_values else 0
            top3_oi_pct = sum(oi_sorted[:3]) / sum(oi_values) if oi_values else 0
            
            # Find most active strike
            most_active_strike = max(strike_volumes.items(), key=lambda x: x[1])[0]
            
            return {
                'top3_volume_concentration': top3_volume_pct,
                'top3_oi_concentration': top3_oi_pct,
                'most_active_strike': most_active_strike,
                'strike_count': len(strike_volumes)
            }
        
        return {
            'top3_volume_concentration': 0.0,
            'top3_oi_concentration': 0.0,
            'most_active_strike': 0.0,
            'strike_count': 0
        }
    
    def _detect_unusual_activity(
        self,
        option_chain: List[Dict],
        historical_avg: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Detect unusual volume activity compared to average.
        
        Simple implementation: Volume/OI ratio anomalies.
        """
        unusual = []
        
        for opt in option_chain:
            strike = opt.get('strike', 0)
            volume = self._get_total_volume(opt)
            oi = self._get_total_oi(opt)
            
            if oi > 0:
                ratio = volume / oi
                
                # Check if ratio is unusually high
                if ratio > self.unusual_threshold:
                    unusual.append({
                        'strike': strike,
                        'volume': volume,
                        'oi': oi,
                        'ratio': ratio,
                        'type': 'HIGH_VOLUME_RATIO'
                    })
        
        # Sort by ratio descending
        unusual.sort(key=lambda x: x['ratio'], reverse=True)
        
        return unusual
    
    def _calculate_liquidity_score(self, option_chain: List[Dict]) -> float:
        """
        Calculate overall liquidity score (0-100).
        
        Based on total OI and volume distribution.
        """
        total_oi = sum(self._get_total_oi(opt) for opt in option_chain)
        strike_count = len(set(opt.get('strike', 0) for opt in option_chain))
        
        # Base score on total OI
        oi_score = min(50, total_oi / 10000 * 50)  # Max 50 points for OI
        
        # Distribution score
        dist_score = min(50, strike_count / 20 * 50)  # Max 50 points for distribution
        
        return oi_score + dist_score
    
    def _determine_sentiment(
        self,
        vol_oi_ratio: float,
        pc_volume: float
    ) -> str:
        """
        Determine market sentiment based on metrics.
        
        Simple rules-based approach.
        """
        # High speculation
        if vol_oi_ratio > 2.5:
            if pc_volume > 1.3:
                return "BEARISH_SPECULATION"
            elif pc_volume < 0.7:
                return "BULLISH_SPECULATION"
            else:
                return "HIGH_SPECULATION"
        
        # Normal activity
        elif 0.5 <= vol_oi_ratio <= 2.5:
            if pc_volume > 1.2:
                return "BEARISH_POSITIONING"
            elif pc_volume < 0.8:
                return "BULLISH_POSITIONING"
            else:
                return "NEUTRAL"
        
        # Low activity (hedging)
        else:
            return "HEDGING_ACTIVITY"
    
    def _get_total_volume(self, option: Dict) -> float:
        """Get total volume for an option."""
        return (option.get('call_volume', 0) + 
                option.get('put_volume', 0))
    
    def _get_total_oi(self, option: Dict) -> float:
        """Get total open interest for an option."""
        return (option.get('call_open_interest', 0) + 
                option.get('put_open_interest', 0))
    
    def _empty_volume_result(self) -> Dict[str, float]:
        """Return empty result for error cases."""
        return {
            'volume_oi_ratio': 0.0,
            'put_call_volume': 1.0,
            'put_call_oi': 1.0,
            'strike_concentration': {},
            'unusual_activity_count': 0,
            'unusual_strikes': [],
            'liquidity_score': 0.0,
            'sentiment': 'UNKNOWN',
            'total_volume': 0,
            'total_oi': 0
        }
    
    def get_strategy_volume_adjustments(
        self,
        strategy_type: str,
        volume_data: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate scoring adjustments based on volume/OI for different strategies.
        
        Ship-fast implementation: Simple sentiment-based rules.
        """
        adjustments = {
            'volume_adjustment': 0.0,
            'liquidity_bonus': 0.0,
            'sentiment_adjustment': 0.0
        }
        
        # Liquidity bonus for all strategies
        liquidity = volume_data.get('liquidity_score', 0)
        if liquidity > 80:
            adjustments['liquidity_bonus'] = 5.0
        elif liquidity > 60:
            adjustments['liquidity_bonus'] = 3.0
        
        # Volume/OI ratio adjustments
        vol_oi = volume_data.get('volume_oi_ratio', 1.0)
        sentiment = volume_data.get('sentiment', 'NEUTRAL')
        
        if strategy_type == "Butterfly":
            # Butterflies prefer stable markets
            if vol_oi < 1.5 and sentiment in ['NEUTRAL', 'HEDGING_ACTIVITY']:
                adjustments['volume_adjustment'] = 4.0
                
        elif strategy_type == "Iron_Condor":
            # Iron Condors also prefer low speculation
            if sentiment in ['NEUTRAL', 'HEDGING_ACTIVITY']:
                adjustments['sentiment_adjustment'] = 3.0
            # But need good liquidity
            if liquidity < 40:
                adjustments['liquidity_bonus'] = -3.0
                
        elif strategy_type == "Vertical":
            # Verticals can handle speculation
            if sentiment in ['BULLISH_SPECULATION', 'BEARISH_SPECULATION']:
                adjustments['sentiment_adjustment'] = 2.0
            # High volume is good for entry/exit
            if vol_oi > 2.0:
                adjustments['volume_adjustment'] = 2.0
        
        return adjustments


# Example usage and testing
if __name__ == "__main__":
    # Test the wrapper
    vol_wrapper = VolumeOIWrapper()
    
    # Mock option chain data
    mock_chain = [
        {
            'strike': 5800,
            'call_volume': 2500,
            'put_volume': 1800,
            'call_open_interest': 5000,
            'put_open_interest': 3000
        },
        {
            'strike': 5850,
            'call_volume': 12000,  # Unusual activity
            'put_volume': 8000,
            'call_open_interest': 8000,
            'put_open_interest': 6000
        },
        {
            'strike': 5900,
            'call_volume': 1000,
            'put_volume': 3500,
            'call_open_interest': 4000,
            'put_open_interest': 7000
        }
    ]
    
    # Analyze volume/OI
    analysis = vol_wrapper.analyze(mock_chain)
    
    print("Volume/OI Analysis:")
    print(f"Volume/OI Ratio: {analysis['volume_oi_ratio']:.2f}")
    print(f"Put/Call Volume: {analysis['put_call_volume']:.2f}")
    print(f"Put/Call OI: {analysis['put_call_oi']:.2f}")
    print(f"Liquidity Score: {analysis['liquidity_score']:.1f}")
    print(f"Sentiment: {analysis['sentiment']}")
    print(f"Unusual Activity Count: {analysis['unusual_activity_count']}")
    
    if analysis['unusual_strikes']:
        print("\nUnusual Activity Detected:")
        for unusual in analysis['unusual_strikes']:
            print(f"  Strike {unusual['strike']}: Volume/OI = {unusual['ratio']:.2f}")
    
    # Test strategy adjustments
    for strategy in ["Butterfly", "Iron_Condor", "Vertical"]:
        adj = vol_wrapper.get_strategy_volume_adjustments(strategy, analysis)
        print(f"\n{strategy} volume adjustments: {adj}")
