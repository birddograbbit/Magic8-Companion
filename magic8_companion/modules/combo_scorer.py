from typing import Dict


def score_combo_types(magic8_data: Dict, market_analysis: Dict) -> Dict[str, int]:
    """Score combo types using Magic8 + market data"""
    spot = magic8_data.get('spot_price')
    trend_strength = magic8_data.get('strength', 0)
    range_size = magic8_data.get('range', 0)
    center = magic8_data.get('levels', {}).get('center', spot)

    iv_rank = market_analysis.get('iv_percentile', 50)
    gex_distance = abs(spot - market_analysis.get('gex_flip', spot)) / spot if spot else 0

    scores = {}

    # Butterfly
    butterfly_score = 0
    if spot and abs(spot - center) / spot < 0.005:
        butterfly_score += 30
    if range_size < 15:
        butterfly_score += 25
    if trend_strength < 0.6:
        butterfly_score += 20
    if gex_distance < 0.01:
        butterfly_score += 15
    if iv_rank > 50:
        butterfly_score += 10

    # Iron Condor
    condor_score = 0
    if range_size < 25:
        condor_score += 35
    if 0.3 <= trend_strength <= 0.7:
        condor_score += 30
    if iv_rank > 40:
        condor_score += 20
    if gex_distance < 0.02:
        condor_score += 15

    # Vertical
    vertical_score = 0
    if trend_strength > 0.6:
        vertical_score += 40
    if range_size > 20:
        vertical_score += 30
    if iv_rank > 30:
        vertical_score += 20
    if gex_distance > 0.02:
        vertical_score += 10

    scores['butterfly'] = min(butterfly_score, 100)
    scores['iron_condor'] = min(condor_score, 100)
    scores['vertical'] = min(vertical_score, 100)
    return scores


def generate_recommendation(scores: Dict[str, int]) -> Dict:
    """Generate combo type recommendation"""
    best_combo = max(scores, key=scores.get)
    best_score = scores[best_combo]
    if best_score >= 70:
        second_best = sorted(scores.values())[-2]
        if best_score - second_best >= 15:
            return {
                'recommendation': best_combo,
                'score': best_score,
                'confidence': 'HIGH' if best_score >= 85 else 'MEDIUM',
            }
    return {'recommendation': 'NONE', 'reason': 'No clear favorite'}
