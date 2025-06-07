from magic8_companion.modules.combo_scorer import score_combo_types, generate_recommendation


def test_generate_recommendation():
    magic8 = {
        'spot_price': 5000,
        'strength': 0.5,
        'range': 10,
        'levels': {'center': 5000}
    }
    market = {'iv_percentile': 60, 'gex_flip': 5000, 'spread_avg': 1}
    scores = score_combo_types(magic8, market)
    rec = generate_recommendation(scores)
    assert 'recommendation' in rec
