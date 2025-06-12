"""
Magic8-Companion Integration for DiscordTrading System

This module reads Magic8-Companion recommendations and provides filtering
logic for the DiscordTrading system to determine which trade types to execute.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class Magic8CompanionIntegration:
    """Integration layer between Magic8-Companion and DiscordTrading."""
    
    def __init__(self, recommendations_file: str = "data/recommendations.json"):
        """Initialize the integration."""
        self.recommendations_file = Path(recommendations_file)
        self.cache = {}
        self.cache_expiry = None
        self.cache_duration = timedelta(minutes=30)  # Cache for 30 minutes
        
    def should_execute_strategy(self, symbol: str, strategy_type: str) -> bool:
        """
        Check if a strategy should be executed based on Magic8-Companion recommendations.
        
        Args:
            symbol: Trading symbol (e.g., "SPX", "SPY")
            strategy_type: Strategy type ("Butterfly", "Sonar"/"Iron_Condor", "Vertical")
            
        Returns:
            True if strategy should be executed, False otherwise
        """
        try:
            recommendations = self._get_recommendations()
            
            if not recommendations:
                logger.debug("No Magic8-Companion recommendations available, allowing all strategies")
                return True  # Default to allow if no recommendations
            
            # Map strategy names (DiscordTrading uses "Sonar", Magic8-Companion uses "Iron_Condor")
            mapped_strategy = self._map_strategy_name(strategy_type)

            # Get recommendation for this symbol
            symbol_rec = recommendations.get("recommendations", {}).get(symbol)

            if not symbol_rec:
                logger.debug(f"No Magic8-Companion recommendation for {symbol}, allowing {strategy_type}")
                return True  # Allow if no specific recommendation for symbol

            strategies = symbol_rec.get("strategies")

            if strategies:
                strategy_data = strategies.get(mapped_strategy)

                if not strategy_data:
                    logger.debug(
                        f"No strategy data for {mapped_strategy} on {symbol}; allowing {strategy_type}"
                    )
                    return True

                should_trade = strategy_data.get("should_trade", True)
                confidence = strategy_data.get(
                    "confidence", symbol_rec.get("confidence", "MEDIUM")
                )

                if should_trade:
                    logger.info(
                        f"✅ {symbol} {strategy_type}: APPROVED by Magic8-Companion ({confidence})"
                    )
                    return True

                logger.info(
                    f"🚫 {symbol} {strategy_type}: BLOCKED by Magic8-Companion ({confidence})"
                )
                return False

            # Fallback for older recommendation format
            preferred_strategy = symbol_rec.get("preferred_strategy")
            confidence = symbol_rec.get("confidence", "MEDIUM")

            is_preferred = mapped_strategy == preferred_strategy

            if is_preferred:
                logger.info(
                    f"✅ {symbol} {strategy_type}: RECOMMENDED by Magic8-Companion ({confidence} confidence)"
                )
                return True

            logger.info(
                f"🚫 {symbol} {strategy_type}: NOT recommended by Magic8-Companion (prefers {preferred_strategy})"
            )
            return False
                
        except Exception as e:
            logger.error(f"Error checking Magic8-Companion recommendation: {e}")
            return True  # Default to allow on error
    
    def get_recommendation_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the current recommendation summary for a symbol."""
        try:
            recommendations = self._get_recommendations()
            
            if not recommendations:
                return None
                
            return recommendations.get("recommendations", {}).get(symbol)
            
        except Exception as e:
            logger.error(f"Error getting recommendation summary: {e}")
            return None
    
    def get_all_recommendations(self) -> Optional[Dict[str, Any]]:
        """Get all current recommendations."""
        return self._get_recommendations()
    
    def log_recommendation_status(self):
        """Log current recommendation status for all symbols."""
        try:
            recommendations = self._get_recommendations()
            
            if not recommendations:
                logger.info("📊 Magic8-Companion: No recommendations available")
                return
                
            checkpoint_time = recommendations.get("checkpoint_time", "Unknown")
            logger.info(f"📊 Magic8-Companion Recommendations ({checkpoint_time}):")
            
            recs = recommendations.get("recommendations", {})
            if not recs:
                logger.info("  No specific recommendations this checkpoint")
                return
                
            for symbol, rec in recs.items():
                strategies = rec.get("strategies")

                if strategies:
                    logger.info(f"  {symbol} recommendations:")
                    for strat_name, strat_data in strategies.items():
                        score = strat_data.get("score", 0)
                        confidence = strat_data.get("confidence", "MEDIUM")
                        trade = strat_data.get("should_trade", False)
                        status = "✅ TRADE" if trade else "⏭️  SKIP"
                        logger.info(
                            f"    {strat_name}: {confidence} ({score}) - {status}"
                        )
                else:
                    strategy = rec.get("preferred_strategy", "Unknown")
                    score = rec.get("score", 0)
                    confidence = rec.get("confidence", "MEDIUM")
                    logger.info(
                        f"  {symbol}: {strategy} (Score: {score}, {confidence})"
                    )
                
        except Exception as e:
            logger.error(f"Error logging recommendation status: {e}")
    
    def _get_recommendations(self) -> Optional[Dict[str, Any]]:
        """Get recommendations from file with caching."""
        now = datetime.now()
        
        # Check cache first
        if (self.cache and self.cache_expiry and now < self.cache_expiry):
            return self.cache
        
        # Load from file
        try:
            if not self.recommendations_file.exists():
                logger.debug(f"Recommendations file not found: {self.recommendations_file}")
                return None
                
            with open(self.recommendations_file, 'r') as f:
                data = json.load(f)
            
            # Check if data is recent (within last 2 hours)
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                age = datetime.now(timestamp.tzinfo) - timestamp
                
                if age > timedelta(hours=2):
                    logger.warning(f"Magic8-Companion recommendations are stale ({age})")
                    return None
            
            # Update cache
            self.cache = data
            self.cache_expiry = now + self.cache_duration
            
            logger.debug(f"Loaded Magic8-Companion recommendations: {len(data.get('recommendations', {}))} symbols")
            return data
            
        except Exception as e:
            logger.error(f"Error loading recommendations file: {e}")
            return None
    
    def _map_strategy_name(self, strategy_type: str) -> str:
        """Map DiscordTrading strategy names to Magic8-Companion names."""
        mapping = {
            "Sonar": "Iron_Condor",
            "Iron Condor": "Iron_Condor", 
            "IronCondor": "Iron_Condor",
            "Butterfly": "Butterfly",
            "Vertical": "Vertical"
        }
        
        return mapping.get(strategy_type, strategy_type)


# Global instance for easy import
magic8_integration = Magic8CompanionIntegration()


def should_execute_strategy(symbol: str, strategy_type: str) -> bool:
    """Convenience function for checking if strategy should execute."""
    return magic8_integration.should_execute_strategy(symbol, strategy_type)


def log_current_recommendations():
    """Convenience function for logging current recommendations."""
    magic8_integration.log_recommendation_status()


# Example usage for DiscordTrading integration:
"""
# In discord_trading_bot.py, before executing a trade:

from magic8_companion_integration import should_execute_strategy, log_current_recommendations

# Log current recommendations on startup
log_current_recommendations()

# Before executing a trade, check if it's recommended:
if should_execute_strategy(symbol, trade_type):
    logger.info(f"Executing {trade_type} for {symbol} (approved by Magic8-Companion)")
    # Execute trade...
else:
    logger.info(f"Skipping {trade_type} for {symbol} (not recommended by Magic8-Companion)")
    # Skip this trade
"""
