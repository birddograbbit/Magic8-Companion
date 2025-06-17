from magic8_companion.unified_main import RecommendationEngine

def test_should_trade_high_only():
    engine = RecommendationEngine()
    scores = {"Butterfly": 80, "Iron_Condor": 65, "Vertical": 55}
    market_data = {"iv_percentile": 30, "expected_range_pct": 0.01}
    result = engine._build_all_recommendations(scores, market_data, "SPX")
    strategies = result["strategies"]
    assert strategies["Butterfly"]["should_trade"] is True
    assert strategies["Iron_Condor"]["should_trade"] is False
    assert strategies["Vertical"]["should_trade"] is False
