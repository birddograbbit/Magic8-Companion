import asyncio
import pytest
from magic8_companion.wrappers.enhanced_gex_wrapper import EnhancedGEXWrapper

def test_wrapper_uses_market_data(monkeypatch):
    wrapper = EnhancedGEXWrapper()

    market_data = {
        'option_chain': [
            {'strike': 100, 'call_gamma': 0.1, 'put_gamma': 0.2, 'call_oi': 10, 'put_oi': 10, 'dte': 0}
        ],
        'current_price': 100
    }

    called = {'native': 0}

    async def fake_run(*args, **kwargs):
        raise AssertionError("run_gamma_analysis should not be called")

    def fake_calc(self, symbol, md):
        called['native'] += 1
        return {
            'symbol': symbol,
            'timestamp': '2025-01-01T00:00:00',
            'net_gex': 1_000_000,
            'levels': {'zero_gamma': 99, 'call_wall': 110, 'put_wall': 90},
            'regime_analysis': {'regime': 'positive', 'bias': 'neutral', 'confidence': 'high'},
        }

    monkeypatch.setattr('magic8_companion.wrappers.enhanced_gex_wrapper.run_gamma_analysis', fake_run)
    monkeypatch.setattr('magic8_companion.modules.native_gex_analyzer.NativeGEXAnalyzer.calculate_gamma_exposure', fake_calc)

    result = asyncio.run(wrapper.get_gamma_adjustments(symbol='SPX', market_data=market_data))
    assert called['native'] == 1
    assert result['gamma_metrics']['gamma_flip'] == 99

def test_wrapper_uses_cache(monkeypatch):
    wrapper = EnhancedGEXWrapper()

    market_data = {
        'option_chain': [
            {'strike': 100, 'call_gamma': 0.1, 'put_gamma': 0.2, 'call_oi': 10, 'put_oi': 10, 'dte': 0}
        ],
        'current_price': 100
    }

    called = {'native': 0}

    def fake_calc(self, symbol, md):
        called['native'] += 1
        return {
            'symbol': symbol,
            'timestamp': '2025-01-01T00:00:00',
            'net_gex': 1_000_000,
            'levels': {'zero_gamma': 99},
            'regime_analysis': {'regime': 'positive', 'bias': 'neutral', 'confidence': 'high'},
        }

    async def fake_run(*args, **kwargs):
        raise AssertionError("run_gamma_analysis should not be called")

    monkeypatch.setattr('magic8_companion.wrappers.enhanced_gex_wrapper.run_gamma_analysis', fake_run)
    monkeypatch.setattr('magic8_companion.modules.native_gex_analyzer.NativeGEXAnalyzer.calculate_gamma_exposure', fake_calc)

    result1 = asyncio.run(wrapper.get_gamma_adjustments(symbol='SPX', market_data=market_data))
    result2 = asyncio.run(wrapper.get_gamma_adjustments(symbol='SPX', market_data=market_data))

    assert called['native'] == 1
    assert result1 == result2
