"""
Gamma Runner for Magic8-Companion.
Main entry point for running gamma analysis on symbols.
"""
import logging
import json
import os
from typing import Dict, Optional, List
from datetime import datetime
import asyncio
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from magic8_companion.data_providers import get_provider
from magic8_companion.analysis.gamma import (
    GammaExposureCalculator,
    GammaLevels,
    MarketRegimeAnalyzer
)
from magic8_companion.unified_config import settings

logger = logging.getLogger(__name__)


async def run_gamma_analysis(symbol: str,
                             data_provider: Optional[str] = None,
                             save_results: bool = True,
                             output_dir: str = "data/gamma_analysis") -> Optional[Dict]:
    """
    Run complete gamma analysis for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., 'SPX', 'SPY')
        data_provider: Provider name (ib, yahoo, file). Uses settings default if None
        save_results: Whether to save results to file
        output_dir: Directory to save results
        
    Returns:
        Dict with complete gamma analysis or None if failed
    """
    try:
        logger.info(f"Starting gamma analysis for {symbol}")
        
        # Get data provider
        provider = get_provider(data_provider)
        if not await provider.is_connected():
            logger.error(f"Data provider {data_provider or settings.data_provider} not connected")
            return None
        
        # Get option chain data
        logger.info(f"Fetching option chain for {symbol}")
        market_data = await provider.get_option_chain(symbol)
        
        if not market_data or 'option_chain' not in market_data:
            logger.error(f"No option chain data available for {symbol}")
            return None
        
        # Get spot price
        spot_price = market_data.get('current_price') or await provider.get_spot_price(symbol)
        if not spot_price:
            logger.error(f"No spot price available for {symbol}")
            return None
        
        # Initialize components
        spot_multiplier = settings.get_gamma_spot_multiplier(symbol)
        calculator = GammaExposureCalculator(spot_multiplier=spot_multiplier)
        levels_analyzer = GammaLevels()
        regime_analyzer = MarketRegimeAnalyzer()
        
        # Calculate GEX
        logger.info(f"Calculating GEX for {symbol}")
        gex_data = calculator.calculate_gex(
            spot_price=spot_price,
            option_chain=market_data['option_chain'],
            use_0dte_multiplier=True,
            dte_multiplier=settings.gex_0dte_multiplier
        )
        
        # Find levels
        logger.info(f"Analyzing gamma levels for {symbol}")
        gex_data['levels'] = levels_analyzer.find_levels(
            gex_data['strike_gex'],
            spot_price
        )
        
        # Analyze regime
        logger.info(f"Analyzing market regime for {symbol}")
        gex_data['regime_analysis'] = regime_analyzer.analyze_regime(
            gex_data,
            spot_price
        )
        
        # Add metadata
        gex_data['symbol'] = symbol
        gex_data['data_provider'] = data_provider or settings.data_provider
        gex_data['analysis_timestamp'] = datetime.now().isoformat()
        
        # Save results if requested
        if save_results:
            _save_results(gex_data, symbol, output_dir)
        
        # Log summary
        _log_summary(gex_data)
        
        return gex_data
        
    except Exception as e:
        logger.error(f"Error running gamma analysis for {symbol}: {e}", exc_info=True)
        return None


async def run_batch_gamma_analysis(symbols: Optional[List[str]] = None,
                                   data_provider: Optional[str] = None) -> Dict[str, Dict]:
    """
    Run gamma analysis for multiple symbols.
    
    Args:
        symbols: List of symbols. Uses settings.gamma_symbols if None
        data_provider: Data provider to use
        
    Returns:
        Dict mapping symbol to analysis results
    """
    if symbols is None:
        symbols = settings.gamma_symbols
    
    results = {}
    
    for symbol in symbols:
        logger.info(f"Running batch analysis for {symbol}")
        result = await run_gamma_analysis(symbol, data_provider)
        if result:
            results[symbol] = result
        else:
            logger.warning(f"Failed to analyze {symbol}")
    
    return results


def _save_results(gex_data: Dict, symbol: str, output_dir: str) -> None:
    """Save gamma analysis results to file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_gamma_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(gex_data, f, indent=2, default=str)
        
        logger.info(f"Saved gamma analysis to {filepath}")
        
        # Also save latest analysis (overwrite)
        latest_filepath = os.path.join(output_dir, f"{symbol}_gamma_latest.json")
        with open(latest_filepath, 'w') as f:
            json.dump(gex_data, f, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error saving results: {e}")


def _log_summary(gex_data: Dict) -> None:
    """Log summary of gamma analysis."""
    symbol = gex_data.get('symbol', 'Unknown')
    net_gex = gex_data.get('net_gex', 0)
    regime = gex_data.get('regime', 'unknown')
    levels = gex_data.get('levels', {})
    regime_analysis = gex_data.get('regime_analysis', {})
    
    logger.info(f"""
    === Gamma Analysis Summary for {symbol} ===
    Net GEX: ${net_gex:,.0f} ({net_gex/1e9:.2f}B)
    Regime: {regime} ({regime_analysis.get('magnitude', 'unknown')} magnitude)
    Bias: {regime_analysis.get('bias', 'unknown')}
    Call Wall: {levels.get('call_wall', 'N/A')}
    Put Wall: {levels.get('put_wall', 'N/A')}
    Zero Gamma: {levels.get('zero_gamma', 'N/A')}
    Expected Behavior: {regime_analysis.get('expected_behavior', {}).get('description', 'N/A')}
    """)


# Allow running as script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run gamma analysis")
    parser.add_argument("symbol", help="Symbol to analyze")
    parser.add_argument("--provider", help="Data provider (ib, yahoo, file)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run analysis
    results = asyncio.run(
        run_gamma_analysis(
            symbol=args.symbol,
            data_provider=args.provider,
            save_results=not args.no_save,
        )
    )
    
    if results:
        print(json.dumps(results, indent=2, default=str))
    else:
        print("Gamma analysis failed")
        sys.exit(1)
