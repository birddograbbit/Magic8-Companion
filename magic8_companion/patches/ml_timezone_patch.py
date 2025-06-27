"""Temporary patch for MLOptionTrading timezone bug."""
import logging
from datetime import timedelta
import pytz

logger = logging.getLogger(__name__)


def apply_patch():
    try:
        from ml.enhanced_ml_system import FeatureEngineer
    except Exception as e:  # pragma: no cover - patch only if module present
        logger.debug(f"ML library not available: {e}")
        return

    if getattr(FeatureEngineer.create_temporal_features, "_patched", False):
        return

    original = FeatureEngineer.create_temporal_features

    def patched_create_temporal_features(self, current_time):
        """Handle aware datetimes gracefully and avoid pytz errors."""
        naive_time = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        try:
            return original(self, naive_time)
        except ValueError as err:
            if "Not naive datetime" not in str(err):
                raise
            est_time = self.est.localize(naive_time)
            offset_today = est_time.utcoffset() or timedelta()
            offset_prev = (est_time - timedelta(days=1)).utcoffset() or timedelta()
            offset_tomorrow = (est_time + timedelta(days=1)).utcoffset() or timedelta()
            return {
                "hour_of_day": est_time.hour,
                "day_of_week": est_time.weekday(),
                "offset_today": offset_today.total_seconds() / 3600,
                "offset_prev": offset_prev.total_seconds() / 3600,
                "offset_tomorrow": offset_tomorrow.total_seconds() / 3600,
            }

    patched_create_temporal_features._patched = True
    FeatureEngineer.create_temporal_features = patched_create_temporal_features
    logger.info("Applied MLOptionTrading timezone patch")


apply_patch()
