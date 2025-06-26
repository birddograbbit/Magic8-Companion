#!/usr/bin/env python3
"""Monitor 5-minute ML prediction performance"""

import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def monitor_predictions():
    data_dir = Path('data')
    stats = defaultdict(lambda: {
        'predictions': 0,
        'high_confidence': 0,
        'strategies': defaultdict(int),
        'last_update': None
    })

    print("Monitoring 5-minute ML predictions...")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            ml_file = data_dir / 'ml_predictions_5min.json'
            if ml_file.exists():
                with open(ml_file) as f:
                    data = json.load(f)
                for symbol, rec in data['recommendations'].items():
                    strategy = rec['best_strategy']
                    confidence = rec['strategies'][strategy]['confidence']

                    stats[symbol]['predictions'] += 1
                    if confidence == 'HIGH':
                        stats[symbol]['high_confidence'] += 1
                    stats[symbol]['strategies'][strategy] += 1
                    stats[symbol]['last_update'] = data['timestamp']

            print("\033[H\033[J")
            print("=== 5-Minute ML Predictions Monitor ===")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            for symbol, s in stats.items():
                if s['predictions'] > 0:
                    print(f"{symbol}:")
                    print(f"  Total predictions: {s['predictions']}")
                    print(f"  High confidence rate: {s['high_confidence']/s['predictions']:.1%}")
                    print(f"  Strategies: {dict(s['strategies'])}")
                    print(f"  Last update: {s['last_update']}\n")

            time.sleep(30)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == '__main__':
    monitor_predictions()
