from magic8_companion.analysis.gamma.gamma_exposure import GammaExposureAnalyzer


def test_call_wall_detection_with_negative_call_gex():
    analyzer = GammaExposureAnalyzer()
    spot = 100
    # Call gex negative, put gex positive to get net positive above spot
    strike_gex = {
        95: -100000,
        100: 0,
        105: 50000,  # positive net gex above spot
        110: -20000,
        115: 30000
    }
    levels = analyzer._find_key_levels(strike_gex, spot)
    assert levels['call_wall'] == 105


def test_put_wall_detection_with_positive_put_gex():
    analyzer = GammaExposureAnalyzer()
    spot = 100
    strike_gex = {
        90: -50000,  # most negative net gex below spot
        95: -10000,
        100: 0,
        105: 20000,
        110: 30000
    }
    levels = analyzer._find_key_levels(strike_gex, spot)
    assert levels['put_wall'] == 90
