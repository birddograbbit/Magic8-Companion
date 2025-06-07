from typing import Dict
import numpy as np
from .. import gex_analysis


def get_market_analysis(ib_client) -> Dict:
    """Lightweight market analysis for combo scoring"""
    # For MVP, return static placeholders or simple calculations
    iv_percentile = 50
    gex_data = gex_analysis.quick_gex_analysis('')  # path would be provided in real setup
    gex_flip = gex_data.get('pinning_analysis', {}).get('zero_gex_level', 0)
    avg_spread = 1.0

    return {
        'iv_percentile': iv_percentile,
        'gex_flip': gex_flip,
        'spread_avg': avg_spread,
    }
