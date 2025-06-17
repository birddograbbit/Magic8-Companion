import pytest
from magic8_companion.wrappers.gex_wrapper import GammaExposureWrapper, OptionData


def test_find_gamma_walls_aggregates():
    wrapper = GammaExposureWrapper()
    options = [
        OptionData(strike=100, call_gamma=0.5, put_gamma=0.1, call_oi=10, put_oi=20, spot_price=100),
        OptionData(strike=100, call_gamma=0.3, put_gamma=0.2, call_oi=15, put_oi=5, spot_price=100),
        OptionData(strike=110, call_gamma=0.4, put_gamma=0.2, call_oi=10, put_oi=10, spot_price=100),
    ]
    walls = wrapper._find_gamma_walls(options, top_n=2)
    assert walls == [100, 110]
