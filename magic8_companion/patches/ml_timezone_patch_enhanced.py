"""Enhanced patch for MLOptionTrading timezone bug."""
import logging
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)


def apply_patch():
    """Apply comprehensive timezone fixes to MLOptionTrading."""
    patches_applied = []
    
    # Patch 1: Fix FeatureEngineer.create_temporal_features
    try:
        from ml.enhanced_ml_system import FeatureEngineer
        
        if not getattr(FeatureEngineer.create_temporal_features, "_patched", False):
            original_create_temporal = FeatureEngineer.create_temporal_features
            
            def patched_create_temporal_features(self, current_time):
                """Handle both naive and aware datetimes properly."""
                # Always ensure we have a naive datetime
                if current_time.tzinfo is not None:
                    logger.debug(f"Stripping timezone from {current_time} (tzinfo={current_time.tzinfo})")
                    naive_time = current_time.replace(tzinfo=None)
                else:
                    naive_time = current_time
                
                try:
                    # First try the original method with naive datetime
                    return original_create_temporal(self, naive_time)
                except ValueError as err:
                    if "Not naive datetime" in str(err):
                        logger.warning(f"Original method still failed with naive datetime, using fallback")
                        # Fallback: manually create the features
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
                    raise
            
            patched_create_temporal_features._patched = True
            FeatureEngineer.create_temporal_features = patched_create_temporal_features
            patches_applied.append("FeatureEngineer.create_temporal_features")
    
    except ImportError as e:
        logger.debug(f"Could not import FeatureEngineer: {e}")
    
    # Patch 2: Fix ProductionMLSystem.predict if needed
    try:
        from ml.enhanced_ml_system import ProductionMLSystem
        
        if not getattr(ProductionMLSystem.predict, "_patched", False):
            original_predict = ProductionMLSystem.predict
            
            def patched_predict(self, **kwargs):
                """Ensure current_time is naive before calling predict."""
                if 'current_time' in kwargs and kwargs['current_time'] is not None:
                    ct = kwargs['current_time']
                    if ct.tzinfo is not None:
                        logger.debug(f"ProductionMLSystem.predict: Converting aware datetime to naive")
                        kwargs['current_time'] = ct.replace(tzinfo=None)
                
                return original_predict(self, **kwargs)
            
            patched_predict._patched = True
            ProductionMLSystem.predict = patched_predict
            patches_applied.append("ProductionMLSystem.predict")
    
    except ImportError as e:
        logger.debug(f"Could not import ProductionMLSystem: {e}")
    
    # Patch 3: Fix any pytz localize calls that might be problematic
    original_localize = pytz.tzinfo.StaticTzInfo.localize
    
    def safe_localize(self, dt, is_dst=False):
        """Safely localize datetime, handling aware datetimes."""
        if dt.tzinfo is not None:
            # If already aware, convert to the target timezone
            logger.debug(f"safe_localize: Converting aware datetime from {dt.tzinfo} to {self}")
            # First make naive, then localize
            naive_dt = dt.replace(tzinfo=None)
            return original_localize(self, naive_dt, is_dst)
        return original_localize(self, dt, is_dst)
    
    # Apply safe_localize to DstTzInfo as well (for timezones with DST)
    if hasattr(pytz.tzinfo, 'DstTzInfo'):
        original_dst_localize = pytz.tzinfo.DstTzInfo.localize
        
        def safe_dst_localize(self, dt, is_dst=False):
            """Safely localize datetime for DST timezones."""
            if dt.tzinfo is not None:
                logger.debug(f"safe_dst_localize: Converting aware datetime from {dt.tzinfo} to {self}")
                naive_dt = dt.replace(tzinfo=None)
                return original_dst_localize(self, naive_dt, is_dst)
            return original_dst_localize(self, dt, is_dst)
        
        pytz.tzinfo.DstTzInfo.localize = safe_dst_localize
        patches_applied.append("pytz.tzinfo.DstTzInfo.localize")
    
    if patches_applied:
        logger.info(f"Applied MLOptionTrading timezone patches: {', '.join(patches_applied)}")
    else:
        logger.warning("No MLOptionTrading timezone patches were applied")


# Auto-apply when imported
apply_patch()
