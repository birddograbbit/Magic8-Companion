"""
Integrated Gamma Analysis Runner for Magic8-Companion
Runs gamma analysis using Magic8's own data providers
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from magic8_companion.analysis.gamma import GammaExposureAnalyzer
from magic8_companion.data_providers import get_provider
from magic8_companion.config import get_config

logger = logging.getLogger(__name__)


class IntegratedGammaRunner:
    """
    Runs gamma analysis using Magic8-Companion's data providers
    """
    
    def __init__(self):
        """Initialize the gamma runner"""
        self.config = get_config()
        self.analyzer = GammaExposureAnalyzer()
        self.data_dir = Path(self.config.data_dir) / 'gamma'
        self.data_dir.mkdir(exist_ok=True)
        
        # Get data provider
        provider_type = self.config.get('M8C_DATA_PROVIDER', 'yahoo')
        self.provider = get_provider(provider_type)
        
        logger.info(f"Gamma runner initialized with {provider_type} provider")
    
    def get_option_chain_data(self, symbol: str = 'SPX'):
        """
        Get option chain using Magic8's data provider
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Tuple of (spot_price, option_chain)
        """
        try:
            # Get underlying data
            underlying_data = self.provider.get_underlying_data(symbol)
            spot_price = underlying_data['price']
            
            logger.info(f"Got {symbol} spot price: ${spot_price:.2f}")
            
            # Get 0DTE option chain
            expiry_date = datetime.now().strftime('%Y-%m-%d')
            option_chain = self.provider.get_option_chain(symbol, expiry_date)
            
            if option_chain.empty:
                logger.warning(f"No option chain data for {symbol}")
                return spot_price, None
            
            # Ensure required columns exist
            required_cols = ['strike', 'call_oi', 'put_oi', 'call_iv', 'put_iv']
            if not all(col in option_chain.columns for col in required_cols):
                logger.warning(f"Missing required columns in option chain")
                return spot_price, None
            
            # Add DTE column if not present
            if 'dte' not in option_chain.columns:
                option_chain['dte'] = 0  # 0DTE
            
            return spot_price, option_chain
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return None, None
    
    def analyze_gamma(self, symbol: str = 'SPX') -> Optional[Dict]:
        """
        Run gamma analysis for a symbol
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Analysis results dictionary
        """
        # Get market data
        spot_price, option_chain = self.get_option_chain_data(symbol)
        
        if not spot_price or option_chain is None:
            logger.error(f"Failed to get market data for {symbol}")
            return None
        
        # Run gamma analysis
        gex_data = self.analyzer.calculate_gex(option_chain, spot_price)
        
        # Get trading signals
        signals = self.analyzer.get_gamma_signals(gex_data, spot_price)
        
        # Calculate score adjustments
        adjustments = self.calculate_score_adjustments(signals)
        
        # Combine results
        results = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'spot_price': spot_price,
            'gamma_metrics': {
                'net_gex': gex_data['net_gex'],
                'call_gex': gex_data['call_gex'],
                'put_gex': gex_data['put_gex'],
                'gamma_flip': gex_data['gamma_flip'],
                'call_wall': gex_data['call_wall'],
                'put_wall': gex_data['put_wall'],
                'expected_move_pct': gex_data['expected_move'] * 100
            },
            'signals': signals,
            'score_adjustments': adjustments
        }
        
        # Save results
        self.save_results(results)
        
        return results
    
    def calculate_score_adjustments(self, signals: Dict) -> Dict:
        """
        Calculate scoring adjustments for different strategies
        
        Args:
            signals: Gamma signals dictionary
            
        Returns:
            Strategy score adjustments
        """
        adjustments = {
            'Butterfly': 0,
            'Iron_Condor': 0,
            'Vertical': 0
        }
        
        # Positive gamma regime favors premium selling
        if signals['gamma_regime'] == 'positive':
            adjustments['Butterfly'] += 15
            adjustments['Iron_Condor'] += 10
        else:
            # Negative gamma favors directional plays
            adjustments['Vertical'] += 10
        
        # Near gamma walls = pinning potential
        if abs(signals.get('distance_to_call_wall', 1)) < 0.005 or \
           abs(signals.get('distance_to_put_wall', 1)) < 0.005:
            adjustments['Butterfly'] += 10
            adjustments['Iron_Condor'] += 5
        
        # Strong signals boost adjustments
        if signals.get('signal_strength') == 'strong':
            for strategy in adjustments:
                adjustments[strategy] = int(adjustments[strategy] * 1.5)
        
        # Cap adjustments at ±20
        for strategy in adjustments:
            adjustments[strategy] = max(-20, min(20, adjustments[strategy]))
        
        return adjustments
    
    def save_results(self, results: Dict):
        """
        Save gamma analysis results
        
        Args:
            results: Analysis results to save
        """
        # Save full results
        with open(self.data_dir / 'gamma_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save simplified adjustments for quick access
        adjustments_output = {
            'timestamp': results['timestamp'],
            'symbol': results['symbol'],
            'score_adjustments': results['score_adjustments'],
            'gamma_regime': results['signals']['gamma_regime'],
            'key_levels': {
                'gamma_flip': results['gamma_metrics']['gamma_flip'],
                'call_wall': results['gamma_metrics']['call_wall'],
                'put_wall': results['gamma_metrics']['put_wall']
            },
            'market_bias': results['signals']['bias']
        }
        
        with open(self.data_dir / 'gamma_adjustments.json', 'w') as f:
            json.dump(adjustments_output, f, indent=2)
        
        logger.info(f"Gamma analysis saved to {self.data_dir}")
    
    def get_latest_analysis(self) -> Optional[Dict]:
        """
        Get the latest gamma analysis results
        
        Returns:
            Latest analysis results or None
        """
        analysis_file = self.data_dir / 'gamma_analysis.json'
        if not analysis_file.exists():
            return None
        
        try:
            with open(analysis_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading gamma analysis: {e}")
            return None


# Convenience function for running analysis
def run_gamma_analysis(symbol: str = 'SPX') -> Optional[Dict]:
    """
    Run gamma analysis for a symbol
    
    Args:
        symbol: Symbol to analyze
        
    Returns:
        Analysis results
    """
    runner = IntegratedGammaRunner()
    return runner.analyze_gamma(symbol)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    results = run_gamma_analysis('SPX')
    if results:
        print(f"\n=== Gamma Analysis Results ===")
        print(f"Symbol: {results['symbol']}")
        print(f"Spot Price: ${results['spot_price']:,.2f}")
        print(f"\nGamma Metrics:")
        print(f"  Net GEX: ${results['gamma_metrics']['net_gex']:,.0f}")
        print(f"  Gamma Flip: ${results['gamma_metrics']['gamma_flip']:,.0f}")
        print(f"  Call Wall: ${results['gamma_metrics']['call_wall']:,.0f}")
        print(f"  Put Wall: ${results['gamma_metrics']['put_wall']:,.0f}")
        print(f"\nScore Adjustments:")
        for strategy, adj in results['score_adjustments'].items():
            print(f"  {strategy}: {adj:+d}")
