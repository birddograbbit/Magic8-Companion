import importlib
import sys
import types
import asyncio
import pandas as pd
import time

ml_pkg = types.ModuleType('ml')
enhanced = types.ModuleType('ml.enhanced_ml_system')
class DummyMLConfig:
    def __init__(self, **kwargs):
        pass
class DummyMLSystem:
    def __init__(self, config):
        self.called_with = None
    def predict(self, *, discord_delta, discord_trades, bar_data, vix_data, current_time):
        self.called_with = current_time
        return {"strategy": "No_Trade", "confidence": 0.0, "details": {}}

enhanced.ProductionMLSystem = DummyMLSystem
enhanced.MLConfig = DummyMLConfig
ml_pkg.enhanced_ml_system = enhanced
sys.modules['ml'] = ml_pkg
sys.modules['ml.enhanced_ml_system'] = enhanced
discord_mod = types.ModuleType('ml.discord_data_processor')
discord_mod.DiscordDataLoader = object
sys.modules['ml.discord_data_processor'] = discord_mod

mls = importlib.reload(importlib.import_module('magic8_companion.ml_scheduler_extension'))


def test_start_scheduler_initial_prediction_uses_naive_datetime(monkeypatch):
    loop = asyncio.new_event_loop()
    scheduler = mls.MLSchedulerExtension(loop=loop, data_provider=None)
    scheduler.ml_system = DummyMLSystem(DummyMLConfig())
    scheduler.bar_data_cache['SPX'] = pd.DataFrame({'close': [100]}, index=[pd.Timestamp('2024-01-01T12:00:00Z')])
    scheduler.vix_data_cache = pd.DataFrame({'close': [15]}, index=[pd.Timestamp('2024-01-01T12:00:00Z')])
    monkeypatch.setattr(scheduler, 'should_run_prediction', lambda: True)
    monkeypatch.setattr(scheduler, 'update_market_data', lambda: None)

    thread = scheduler.start_scheduler()
    time.sleep(0.2)
    scheduler.stop()
    thread.join(timeout=1)

    assert scheduler.ml_system.called_with.tzinfo is None
    loop.close()
