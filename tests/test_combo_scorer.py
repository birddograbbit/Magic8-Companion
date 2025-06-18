import pytest
import asyncio
from magic8_companion.modules.combo_scorer import ComboScorer, generate_recommendation

# Test cases for score_combo_types
# Each tuple: (market_data, expected_scores)
score_test_cases = [
    (
        {
            'iv_percentile': 18,
            'expected_range_pct': 0.003,
            'gamma_environment': 'High Gamma Pinning'
        },
        {'Butterfly': 100, 'Iron_Condor': 30, 'Vertical': 5}
    ),
    (
        {
            'iv_percentile': 50,
            'expected_range_pct': 0.009,
            'gamma_environment': 'Range-bound Moderate'
        },
        {'Butterfly': 0, 'Iron_Condor': 90, 'Vertical': 35}
    ),
    (
        {
            'iv_percentile': 90,
            'expected_range_pct': 0.02,
            'gamma_environment': 'Directional High Volatility'
        },
        {'Butterfly': 0, 'Iron_Condor': 0, 'Vertical': 100}
    ),
    (
        {
            'iv_percentile': 25,
            'expected_range_pct': 0.02,
            'gamma_environment': 'Quiet market'
        },
        {'Butterfly': 25, 'Iron_Condor': 10, 'Vertical': 35}
    ),
]

@pytest.mark.parametrize("market_data, expected_scores", score_test_cases)
def test_score_combo_types_detailed(market_data, expected_scores):
    scorer = ComboScorer()
    scores = asyncio.run(scorer.score_combo_types(market_data, "TEST"))
    assert scores == expected_scores

# Test cases for generate_recommendation
# Each tuple: (scores, expected_recommendation, expected_confidence_or_none)
recommendation_test_cases = [
    ({'butterfly': 85, 'iron_condor': 60, 'vertical': 50}, 'butterfly', 'HIGH'),
    ({'butterfly': 75, 'iron_condor': 50, 'vertical': 40}, 'butterfly', 'MEDIUM'),
    ({'butterfly': 60, 'iron_condor': 80, 'vertical': 55}, 'iron_condor', 'MEDIUM'), # Score 80, diff 20
    ({'butterfly': 60, 'iron_condor': 70, 'vertical': 45}, 'NONE', None),
    ({'butterfly': 90, 'iron_condor': 74, 'vertical': 70}, 'butterfly', 'HIGH'),
    ({'butterfly': 90, 'iron_condor': 76, 'vertical': 70}, 'NONE', None),
    ({'butterfly': 85, 'iron_condor': 70, 'vertical': 65}, 'butterfly', 'HIGH'), # 85-70=15. Should recommend.

    ({'butterfly': 65, 'iron_condor': 60, 'vertical': 50}, 'NONE', None), # Best score < 70
    ({'butterfly': 70, 'iron_condor': 60, 'vertical': 58}, 'NONE', None), # Best score 70, but 70-60=10 < 15 gap
    ({'vertical': 78, 'butterfly': 50, 'iron_condor': 55}, 'vertical', 'MEDIUM'),
]

@pytest.mark.parametrize("scores, expected_rec, expected_conf", recommendation_test_cases)
def test_generate_recommendation_detailed(scores, expected_rec, expected_conf):
    # Assuming default min_recommendation_score = 70 and min_score_gap = 15 from config
    # If these are changed, test cases might need adjustment or config mocking.
    recommendation = generate_recommendation(scores)
    assert recommendation['recommendation'] == expected_rec
    if expected_rec != 'NONE':
        assert recommendation['score'] == scores[expected_rec]
        assert recommendation['confidence'] == expected_conf
    else:
        assert 'reason' in recommendation

# Original basic test (can keep or remove)
def test_generate_recommendation_basic_return_type():
    market = {
        'iv_percentile': 60,
        'expected_range_pct': 0.009,
        'gamma_environment': 'Range-bound moderate'
    }
    scorer = ComboScorer()
    scores = asyncio.run(scorer.score_combo_types(market, "TEST"))
    rec = generate_recommendation(scores)
    assert 'recommendation' in rec
