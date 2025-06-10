#!/usr/bin/env python3
"""
Magic8-Companion - Simplified Trade Type Recommendation Engine

Simplified companion system that analyzes market conditions at scheduled intervals
and outputs trade type recommendations for consumption by DiscordTrading system.

Focus: Ship-fast, minimal complexity, pure recommendation engine.
"""
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any

from .config_simplified import settings
from .modules.market_analysis_simplified import MarketAnalyzer
from .modules.combo_scorer_simplified import ComboScorer
from .utils.scheduler_simplified import SimpleScheduler

# Setup logging
def setup_logging():
    """Configure application logging."""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'magic8_companion.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()


class RecommendationEngine:
    """Core recommendation engine for trade type analysis."""
    
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.combo_scorer = ComboScorer()
        self.output_file = Path(settings.output_file_path)
        self.supported_symbols = settings.supported_symbols
        
    async def generate_recommendations(self) -> Dict[str, Any]:
        """Generate trade type recommendations for all supported symbols."""
        logger.info("Generating trade type recommendations...")
        
        recommendations = {}
        
        for symbol in self.supported_symbols:
            try:
                # Analyze market conditions for this symbol
                market_data = await self.market_analyzer.analyze_symbol(symbol)
                
                if not market_data:
                    logger.warning(f"No market data available for {symbol}")
                    continue
                
                # Score combo types
                scores = self.combo_scorer.score_combo_types(market_data, symbol)
                
                # Build recommendations for ALL strategies
                recommendation = self._build_all_recommendations(scores, market_data, symbol)
                
                if recommendation:
                    recommendations[symbol] = recommendation
                    logger.info(f"{symbol}: Generated recommendations for all strategies")
                
            except Exception as e:
                logger.error(f"Error generating recommendation for {symbol}: {e}")
                
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checkpoint_time": datetime.now().strftime("%H:%M ET"),
            "recommendations": recommendations
        }
    
    def _build_all_recommendations(self, scores: Dict[str, float], market_data: Dict, symbol: str) -> Optional[Dict[str, Any]]:
        """Build recommendations for ALL strategies."""
        if not scores:
            return None
            
        # Build recommendations for each strategy
        strategies = {}
        
        for strategy, score in scores.items():
            # Determine confidence for this strategy
            confidence = self._determine_confidence(score)
            
            # Determine if this strategy should be traded
            should_trade = confidence == "HIGH" and score >= settings.min_recommendation_score
            
            strategies[strategy] = {
                "score": round(score, 1),
                "confidence": confidence,
                "should_trade": should_trade,
                "rationale": self._build_rationale(strategy, market_data, score)
            }
        
        # Find the best strategy for reference
        best_strategy = max(scores.keys(), key=lambda k: scores[k])
        
        return {
            "strategies": strategies,
            "best_strategy": best_strategy,
            "market_conditions": {
                "iv_rank": market_data.get("iv_percentile", "N/A"),
                "range_expectation": market_data.get("expected_range_pct", "N/A"),
                "gamma_environment": market_data.get("gamma_environment", "N/A")
            }
        }
    
    def _determine_confidence(self, score: float) -> str:
        """Determine confidence level based on score."""
        if score >= 75:
            return "HIGH"
        elif score >= 50:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _build_rationale(self, strategy: str, market_data: Dict, score: float) -> str:
        """Build human-readable rationale for recommendation."""
        iv_rank = market_data.get("iv_percentile", 0)
        range_pct = market_data.get("expected_range_pct", 0)
        
        if strategy == "Butterfly":
            return f"Low volatility environment (IV: {iv_rank}%) with tight expected range ({range_pct:.1%})"
        elif strategy == "Iron_Condor":
            return f"Range-bound conditions (Range: {range_pct:.1%}) with moderate volatility (IV: {iv_rank}%)"
        elif strategy == "Vertical":
            return f"Directional opportunity with wide expected range ({range_pct:.1%})"
        else:
            return f"Favorable conditions detected (Score: {score})"
    
    async def save_recommendations(self, recommendations: Dict[str, Any]):
        """Save recommendations to output file."""
        try:
            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first, then move (atomic operation)
            temp_file = self.output_file.with_suffix('.tmp')
            
            with open(temp_file, 'w') as f:
                json.dump(recommendations, f, indent=2)
            
            # Atomic move
            temp_file.replace(self.output_file)
            
            logger.info(f"Recommendations saved to {self.output_file}")
            
            # Log summary for all strategies
            if recommendations.get("recommendations"):
                for symbol, rec in recommendations["recommendations"].items():
                    logger.info(f"📊 {symbol} recommendations:")
                    for strategy, details in rec["strategies"].items():
                        status = "✅ TRADE" if details["should_trade"] else "⏭️  SKIP"
                        logger.info(f"  {strategy}: {details['confidence']} ({details['score']}) - {status}")
            else:
                logger.info("📊 No recommendations generated this checkpoint")
                
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")


class SimplifiedMagic8Companion:
    """Simplified Magic8-Companion application."""
    
    def __init__(self):
        self.recommendation_engine = RecommendationEngine()
        self.scheduler = SimpleScheduler()
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize the application."""
        logger.info("Initializing Magic8-Companion (Simplified)...")
        logger.info(f"Output file: {settings.output_file_path}")
        logger.info(f"Supported symbols: {settings.supported_symbols}")
        logger.info(f"Checkpoints: {settings.checkpoint_times}")
        
        # Setup scheduler
        for checkpoint_time in settings.checkpoint_times:
            self.scheduler.add_checkpoint(checkpoint_time, self.run_checkpoint)
            
        logger.info("Initialization complete")
    
    async def run_checkpoint(self):
        """Execute scheduled checkpoint."""
        try:
            checkpoint_time = datetime.now().strftime("%H:%M ET")
            logger.info(f"🎯 CHECKPOINT {checkpoint_time}")
            
            # Generate recommendations
            recommendations = await self.recommendation_engine.generate_recommendations()
            
            # Save to output file
            await self.recommendation_engine.save_recommendations(recommendations)
            
            # Log summary
            rec_count = len(recommendations.get("recommendations", {}))
            logger.info(f"✅ Checkpoint complete - {rec_count} symbols analyzed")
            
        except Exception as e:
            logger.error(f"Error in checkpoint execution: {e}")
    
    async def run(self):
        """Main application loop."""
        logger.info("Magic8-Companion running...")
        logger.info("Waiting for scheduled checkpoints...")
        
        try:
            # Start scheduler
            await self.scheduler.start()
            
            # Wait for shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Magic8-Companion...")
        
        if self.scheduler:
            await self.scheduler.stop()
            
        logger.info("Shutdown complete")
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.shutdown_event.set()


async def main():
    """Main entry point."""
    print("Starting Magic8-Companion (Simplified Trade Type Recommender)...")
    
    app = SimplifiedMagic8Companion()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)
    
    try:
        await app.initialize()
        await app.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
