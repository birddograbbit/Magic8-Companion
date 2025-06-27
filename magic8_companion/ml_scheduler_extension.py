#!/usr/bin/env python3
"""
ML Scheduler Extension for Magic8-Companion
Provides real-time ML predictions every 5 minutes
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import pandas as pd
import asyncio
import pytz
import schedule
from threading import Thread

# Add paths for MLOptionTrading
MAGIC8_PATH = os.environ.get('MAGIC8_PATH', '.')
ML_PATH = os.environ.get('ML_PATH', '../MLOptionTrading')
sys.path.insert(0, MAGIC8_PATH)
sys.path.insert(0, ML_PATH)

# Import from MLOptionTrading
from ml.enhanced_ml_system import ProductionMLSystem, MLConfig
from ml.discord_data_processor import DiscordDataLoader

# Import from Magic8-Companion
from magic8_companion.data_providers import get_provider
from magic8_companion.unified_config import settings

logger = logging.getLogger(__name__)


class MLSchedulerExtension:
    """Extends Magic8-Companion with 5-minute ML predictions"""

    def __init__(self):
        self.symbols = settings.supported_symbols
        self.output_dir = Path(settings.output_file_path).parent
        self.output_dir.mkdir(exist_ok=True)

        # ML configuration
        self.ml_config = MLConfig(
            enable_two_stage=True,
            confidence_threshold=settings.ml_5min_confidence_threshold,
            direction_model_path=f"{ML_PATH}/models/direction_model.pkl",
            volatility_model_path=f"{ML_PATH}/models/volatility_model.pkl",
        )
        self.ml_system = ProductionMLSystem(self.ml_config)

        # Data provider
        self.data_provider = get_provider(settings.data_provider)

        # Timezone helpers
        self.est = pytz.timezone('US/Eastern')
        self.utc = pytz.UTC

        # Data cache
        self.bar_data_cache: Dict[str, pd.DataFrame] = {}
        self.vix_data_cache: pd.DataFrame | None = None
        self.last_update: datetime | None = None
        self.last_prediction_time: datetime | None = None
        self.max_cache_age = timedelta(minutes=30)
        self.cache_cleanup_interval = 10
        self._prediction_count = 0

        logger.info("ML Scheduler Extension initialized")


    def update_market_data(self):
        """Update market data cache"""
        current_time = datetime.now(self.utc)
        if self.last_update and (current_time - self.last_update).seconds < 60:
            return
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for symbol in self.symbols:
                bars = loop.run_until_complete(
                    self.data_provider.get_historical_data(symbol, "5m", "1d")
                )
                if isinstance(bars, pd.DataFrame) and not bars.empty:
                    self.bar_data_cache[symbol] = bars
                    logger.debug(f"Updated {len(bars)} bars for {symbol}")

            vix_data = loop.run_until_complete(
                self.data_provider.get_historical_data("VIX", "5m", "1d")
            )
            if isinstance(vix_data, pd.DataFrame) and not vix_data.empty:
                self.vix_data_cache = vix_data
                logger.debug(f"Updated {len(vix_data)} VIX bars")
            self.last_update = current_time
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
        finally:
            loop.close()

    def create_delta_features(self, symbol: str, bar_data: pd.DataFrame) -> pd.DataFrame:
        """Create simplified delta features from bar data"""
        if bar_data.empty:
            return pd.DataFrame()
        current_price = bar_data['close'].iloc[-1]
        price_change = bar_data['close'].pct_change().iloc[-1] if len(bar_data) > 1 else 0
        delta_df = pd.DataFrame(index=[bar_data.index[-1]])
        delta_df['CallDelta'] = 0.5 + min(max(price_change * 10, -0.4), 0.4)
        delta_df['PutDelta'] = delta_df['CallDelta'] - 1
        delta_df['delta_spread'] = delta_df['CallDelta'] - abs(delta_df['PutDelta'])
        delta_df['call_put_ratio'] = delta_df['CallDelta'] / abs(delta_df['PutDelta'])
        delta_df['Price'] = current_price
        delta_df['Predicted'] = current_price * (1 + price_change)
        delta_df['price_vs_predicted'] = (current_price - delta_df['Predicted']) / current_price
        return delta_df

    def should_run_prediction(self) -> bool:
        """Determine if a prediction should run based on timing rules."""
        current_time = datetime.now(self.utc)
        et_time = current_time.astimezone(self.est)

        # Skip first and last 5 minutes of regular trading hours
        if et_time.hour == 9 and et_time.minute < 35:
            return False
        if et_time.hour == 15 and et_time.minute >= 55:
            return False

        if self.last_prediction_time and (
            current_time - self.last_prediction_time
        ) < timedelta(minutes=settings.ml_5min_interval):
            return False

        return True

    def run_ml_prediction(self):
        """Run ML prediction for all symbols"""
        if not self.should_run_prediction():
            logger.debug("Skipping 5-minute prediction")
            return

        logger.info("Running 5-minute ML prediction")
        self.update_market_data()
        current_time = datetime.now(self.utc)
        current_time_et = current_time.astimezone(self.est)

        if current_time_et.weekday() >= 5:
            logger.debug("Market closed (weekend)")
            return
        market_open = current_time_et.replace(hour=9, minute=30, second=0)
        market_close = current_time_et.replace(hour=16, minute=0, second=0)
        if not (market_open <= current_time_et <= market_close):
            logger.debug("Outside market hours")
            return

        recommendations = {
            "timestamp": current_time.isoformat(),
            "checkpoint_time": current_time_et.strftime("%H:%M ET"),
            "ml_predictions": True,
            "ml_5min": True,
            "recommendations": {},
        }

        for symbol in self.symbols:
            try:
                bar_data = self.bar_data_cache.get(symbol, pd.DataFrame())
                vix_data = self.vix_data_cache or pd.DataFrame()
                if bar_data.empty:
                    logger.warning(f"No data available for {symbol}")
                    continue
                delta_data = self.create_delta_features(symbol, bar_data)
                trades_data = pd.DataFrame()
                result = self.ml_system.predict(
                    discord_delta=delta_data,
                    discord_trades=trades_data,
                    bar_data=bar_data,
                    vix_data=vix_data,
                    current_time=current_time,
                )
                strategy = result['strategy']
                confidence = result['confidence']
                details = result.get('details', {})
                if confidence >= 0.8:
                    confidence_level = "HIGH"
                elif confidence >= 0.65:
                    confidence_level = "MEDIUM"
                else:
                    confidence_level = "LOW"
                should_trade = confidence_level == "HIGH" and strategy != "No_Trade"
                recommendations["recommendations"][symbol] = {
                    "strategies": {
                        strategy: {
                            "score": confidence * 100,
                            "confidence": confidence_level,
                            "should_trade": should_trade,
                            "ml_confidence": confidence,
                            "direction": details.get('direction', 'neutral'),
                            "volatility_regime": details.get('volatility_regime', 'normal'),
                            "rationale": f"5-min ML: {strategy} ({confidence:.1%})",
                        }
                    },
                    "best_strategy": strategy if should_trade else "No_Trade",
                    "ml_5min_metadata": {
                        "model": "two_stage",
                        "prediction_time": datetime.now().isoformat(),
                    },
                }
                logger.info(
                    f"5-min ML: {symbol} - {strategy} ({confidence:.1%}) - {confidence_level}"
                )
            except Exception as e:
                logger.error(f"Error predicting {symbol}: {e}", exc_info=True)

        ml_output = self.output_dir / "ml_predictions_5min.json"
        with open(ml_output, 'w') as f:
            json.dump(recommendations, f, indent=2)
        self._merge_with_recommendations(recommendations)
        logger.debug(f"5-min ML predictions saved to {ml_output}")
        self.last_prediction_time = current_time
        self._prediction_count += 1
        if self._prediction_count >= self.cache_cleanup_interval:
            self.cleanup_cache()
            self._prediction_count = 0

    def cleanup_cache(self):
        """Remove stale market data from caches."""
        cutoff = datetime.now(self.utc) - self.max_cache_age
        for symbol in list(self.bar_data_cache.keys()):
            df = self.bar_data_cache[symbol]
            self.bar_data_cache[symbol] = df[df.index > cutoff]
        if self.vix_data_cache is not None:
            self.vix_data_cache = self.vix_data_cache[self.vix_data_cache.index > cutoff]

    def _merge_with_recommendations(self, ml_recommendations: Dict):
        """Merge 5-minute ML predictions with existing recommendations"""
        rec_file = self.output_dir / "recommendations.json"
        try:
            if rec_file.exists():
                with open(rec_file, 'r') as f:
                    existing = json.load(f)
            else:
                existing = {"recommendations": {}}
            for symbol, ml_rec in ml_recommendations["recommendations"].items():
                if symbol not in existing["recommendations"]:
                    existing["recommendations"][symbol] = ml_rec
                else:
                    existing_rec = existing["recommendations"][symbol]
                    ml_strategy = ml_rec["best_strategy"]
                    if ml_strategy != "No_Trade":
                        strategy_data = ml_rec["strategies"][ml_strategy].copy()
                        strategy_data["source"] = "ml_5min"
                        existing_rec["strategies"][f"{ml_strategy}_5min"] = strategy_data
                        if strategy_data["confidence"] == "HIGH":
                            current_best = existing_rec.get("best_strategy", "No_Trade")
                            if current_best == "No_Trade" or strategy_data["score"] >= 80:
                                existing_rec["best_strategy"] = ml_strategy
                                existing_rec["best_strategy_source"] = "ml_5min"
            existing["ml_5min_enhanced"] = True
            existing["last_5min_update"] = ml_recommendations["timestamp"]
            with open(rec_file, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            logger.error(f"Error merging recommendations: {e}")

    def start_scheduler(self):
        """Start the 5-minute scheduler"""
        schedule.every(settings.ml_5min_interval).minutes.do(self.run_ml_prediction)
        logger.info("ML 5-minute scheduler started")
        self.run_ml_prediction()

        def run_schedule():
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(10)
        scheduler_thread = Thread(target=run_schedule, daemon=True)
        scheduler_thread.start()
        return scheduler_thread
