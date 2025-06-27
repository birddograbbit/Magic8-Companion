import importlib
import sys
import types
import datetime
import pytz

# Create dummy ml package mimicking the bug
ml_pkg = types.ModuleType('ml')
enhanced = types.ModuleType('ml.enhanced_ml_system')

a = pytz.timezone('US/Eastern')

class DummyFeatureEngineer:
    def __init__(self):
        self.est = a
    def create_temporal_features(self, current_time):
        current_time_est = self.est.localize(current_time)
        return {"offset": self.est.utcoffset(current_time_est).total_seconds()}

class DummyMLConfig:
    pass

class DummyMLSystem:
    def __init__(self, config):
        self.feature_engineer = DummyFeatureEngineer()

ml_pkg.enhanced_ml_system = enhanced
enhanced.FeatureEngineer = DummyFeatureEngineer
enhanced.MLConfig = DummyMLConfig
enhanced.ProductionMLSystem = DummyMLSystem
sys.modules['ml'] = ml_pkg
sys.modules['ml.enhanced_ml_system'] = enhanced

discord_mod = types.ModuleType('ml.discord_data_processor')
discord_mod.DiscordDataLoader = object
sys.modules['ml.discord_data_processor'] = discord_mod

# Apply patch
from magic8_companion.patches.ml_timezone_patch import apply_patch
apply_patch()

import ml.enhanced_ml_system as ems

def test_timezone_patch_handles_aware_datetime():
    fe = ems.FeatureEngineer()
    aware = datetime.datetime.now(pytz.UTC)
    result = fe.create_temporal_features(aware)
    assert 'offset' in result
