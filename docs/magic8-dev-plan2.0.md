# Magic8Clone Development Plan v2.0
## Refined Implementation Guide with Microservice Architecture

*(Version 2.0 - Incorporating best practices from alternative plan analysis)*

---

## Executive Summary

Magic8Clone v2.0 combines the detailed implementation guidance from our initial plan with the superior microservice architecture and specific thresholds from the alternative plan. This refined approach delivers:

- **14-day sprint** to live paper trading (aggressive but achievable)
- **Microservice topology** with Redis pub/sub and PostgreSQL persistence
- **Sub-30s latency** from snapshot to order execution
- **Shadow-live testing** capability against actual Magic8 outputs
- **Docker-compose deployment** for consistent environments

---

## 1. System Architecture

### 1.1 Microservice Topology

```mermaid
flowchart TD
    subgraph Data Layer
        A[IB Gateway/TWS] -->|WebSocket| B[Data Collector Service]
        B --> C[(PostgreSQL)]
        B --> D[Redis Pub/Sub]
    end
    
    subgraph Analytics Layer
        D --> E[Greeks Engine Service]
        D --> F[GEX Calculator Service]
        E --> G[Redis Cache]
        F --> G
    end
    
    subgraph Decision Layer
        G --> H[Combo Selector Service]
        H --> I[Risk Manager Service]
    end
    
    subgraph Execution Layer
        I --> J[Order Manager Service]
        J --> K[IB Execution Gateway]
    end
    
    subgraph Monitoring
        H --> L[Slack Alerts]
        H --> M[Streamlit Dashboard]
        I --> N[Shadow-Live Comparator]
    end
```

### 1.2 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Message Bus** | Redis Streams + Pub/Sub | Low latency, reliable delivery |
| **Data Store** | PostgreSQL + TimescaleDB | Time-series optimization |
| **Cache** | Redis with TTL | Sub-ms Greek lookups |
| **Containerization** | Docker Compose | Dev/prod parity |
| **Monitoring** | Prometheus + Grafana | Real-time KPIs |
| **API Gateway** | FastAPI | REST + WebSocket support |

---

## 2. Core Components Deep Dive

### 2.1 Proven OSS Components (Audited)

| Component | Repository | Key Features | Integration Notes |
|-----------|-----------|--------------|-------------------|
| **ib_async** | [793★](https://github.com/ib-api-reloaded/ib_async) | Async IB client, reconnect logic | Primary data source |
| **py_vollib_vectorized** | [132★](https://github.com/marcdemers/py_vollib_vectorized) | 2.4x faster Greeks | CPU baseline |
| **OptionGreeksGPU** | [PyPI](https://pypi.org/project/OptionGreeksGPU/) | 1500x speedup | Optional, GPL-3 isolated |
| **SPX-Gamma-Exposure** | [131★](https://github.com/jensolson/SPX-Gamma-Exposure) | GEX calculations | Adapt for real-time |
| **0dte-trader** | [56★](https://github.com/aicheung/0dte-trader) | Strategy reference | Fork execution logic |
| **gex-tracker** | [138★](https://github.com/Matteo-Ferrara/gex-tracker) | Visualization | Dashboard integration |

### 2.2 Service Specifications

#### Data Collector Service
```python
# services/data_collector/main.py
import asyncio
from ib_async import IB, Index, Option
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine
import json
from datetime import datetime, timedelta

class DataCollectorService:
    def __init__(self, config):
        self.ib = IB()
        self.redis = redis.Redis.from_url(config['redis_url'])
        self.db_engine = create_async_engine(config['postgres_url'])
        self.config = config
        
    async def start(self):
        """Main service loop"""
        await self.ib.connectAsync(
            self.config['ib_host'], 
            self.config['ib_port'],
            clientId=self.config['ib_client_id']
        )
        
        while True:
            try:
                # Fetch option chain
                chain_data = await self.fetch_0dte_chain()
                
                # Apply quality filters
                filtered_chain = self.apply_filters(chain_data)
                
                # Publish to Redis
                await self.publish_chain(filtered_chain)
                
                # Store in PostgreSQL
                await self.store_chain(filtered_chain)
                
                # Wait for next cycle
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                await self.handle_error(e)
                
    def apply_filters(self, chain_data):
        """Apply quality filters from v1.1"""
        return chain_data[
            (chain_data['spread'] <= 5.0) &  # Max $5 spread
            (chain_data['open_interest'] >= 100) &  # Min 100 OI
            (chain_data['volume'] > 0)  # Has traded today
        ]
        
    async def publish_chain(self, chain_data):
        """Publish to Redis streams"""
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'spot_price': chain_data['spot_price'].iloc[0],
            'chain': chain_data.to_json()
        }
        await self.redis.xadd('option_chain', message)
```

#### Greeks Engine Service
```python
# services/greeks_engine/main.py
import numpy as np
import py_vollib_vectorized as pv
from redis import asyncio as redis
import msgpack

class GreeksEngineService:
    def __init__(self, config):
        self.redis = redis.Redis.from_url(config['redis_url'])
        self.risk_free_rate = config.get('risk_free_rate', 0.05)
        self.use_gpu = config.get('use_gpu', False)
        
        if self.use_gpu and self._check_gpu_cost():
            import OptionGreeksGPU as gpu_greeks
            self.greeks_lib = gpu_greeks
        else:
            self.greeks_lib = pv
            
    def _check_gpu_cost(self):
        """Only use GPU if spot instance < $0.50/hr"""
        # AWS pricing API check
        return True  # Placeholder
        
    async def calculate_greeks_batch(self, option_data):
        """Vectorized Greeks calculation"""
        # Extract arrays
        S = option_data['spot_price'].values
        K = option_data['strike'].values
        T = option_data['dte'].values / 365.0
        r = np.full_like(S, self.risk_free_rate)
        sigma = option_data['iv'].fillna(0.20).values
        flag = option_data['type'].map({'C': 'c', 'P': 'p'}).values
        
        # Calculate all Greeks at once
        greeks = {
            'delta': self.greeks_lib.delta(flag, S, K, T, r, sigma),
            'gamma': self.greeks_lib.gamma(flag, S, K, T, r, sigma),
            'theta': self.greeks_lib.theta(flag, S, K, T, r, sigma),
            'vega': self.greeks_lib.vega(flag, S, K, T, r, sigma),
            'rho': self.greeks_lib.rho(flag, S, K, T, r, sigma)
        }
        
        # Cache results
        cache_key = f"greeks:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        await self.redis.setex(
            cache_key,
            300,  # 5 min TTL
            msgpack.packb(greeks)
        )
        
        return greeks
```

#### Combo Selector Service
```python
# services/combo_selector/main.py
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class ComboRecommendation:
    strategy: str
    legs: List[dict]
    credit: float
    max_loss: float
    probability: float
    score: float
    rationale: str

class ComboSelectorService:
    """Rule-based strategy selection with v1.1 thresholds"""
    
    def __init__(self, config):
        self.config = config
        self.redis = redis.Redis.from_url(config['redis_url'])
        
    async def select_combos(self, chain_data, greeks, gex_data):
        """Main selection logic with specific thresholds"""
        
        # Calculate market metrics
        spot = chain_data['spot_price'].iloc[0]
        atr_5min = await self.get_5min_atr(spot)
        expected_range = atr_5min * 3  # ATR × 3 rule
        range_pct = expected_range / spot
        
        # GEX analysis
        gex_flip = gex_data['zero_gamma_level']
        gex_distance_pct = abs(spot - gex_flip) / spot
        
        recommendations = []
        
        # Iron Condor: Range < 0.6%
        if range_pct < 0.006:
            ic = self._build_iron_condor(chain_data, greeks, 
                                        target_delta=0.10)  # 10-15Δ wings
            if ic and ic.score > 70:
                recommendations.append(ic)
                
        # Unbalanced Butterfly: Center at GEX flip
        if gex_flip and abs(gex_distance_pct) < 0.01:
            bf = self._build_butterfly(chain_data, greeks,
                                     center_strike=gex_flip,
                                     max_debit_pct=0.002)  # 0.2% notional
            if bf and bf.score > 75:
                recommendations.append(bf)
                
        # Directional Vertical: Distance > 0.4%
        if gex_distance_pct > 0.004:
            direction = 'bull' if spot < gex_flip else 'bear'
            vert = self._build_vertical(chain_data, greeks,
                                      direction=direction)
            if vert and vert.score > 65:
                recommendations.append(vert)
                
        # Sort by score and publish
        recommendations.sort(key=lambda x: x.score, reverse=True)
        await self._publish_recommendations(recommendations[:3])
        
        return recommendations[:3]
        
    def _build_iron_condor(self, chain_data, greeks, target_delta):
        """Build IC with 10-15Δ wings"""
        puts = chain_data[chain_data['type'] == 'P']
        calls = chain_data[chain_data['type'] == 'C']
        
        # Find strikes at target deltas
        short_put = self._find_by_delta(puts, -target_delta)
        long_put = self._find_by_delta(puts, -target_delta * 0.5)
        short_call = self._find_by_delta(calls, target_delta)
        long_call = self._find_by_delta(calls, target_delta * 0.5)
        
        if not all([short_put, long_put, short_call, long_call]):
            return None
            
        # Calculate P&L
        credit = (
            short_put['bid'] + short_call['bid'] -
            long_put['ask'] - long_call['ask']
        )
        
        width = short_call['strike'] - long_call['strike']
        max_loss = (width - credit) * 100
        
        # Probability of profit (rough estimate)
        pop = 0.68 if target_delta <= 0.15 else 0.60
        
        # Score based on risk/reward
        score = min(100, (credit / max_loss) * 200 * pop)
        
        return ComboRecommendation(
            strategy='iron_condor',
            legs=[
                {'action': 'SELL', 'strike': short_put['strike'], 
                 'type': 'P', 'delta': short_put['delta']},
                {'action': 'BUY', 'strike': long_put['strike'], 
                 'type': 'P', 'delta': long_put['delta']},
                {'action': 'SELL', 'strike': short_call['strike'], 
                 'type': 'C', 'delta': short_call['delta']},
                {'action': 'BUY', 'strike': long_call['strike'], 
                 'type': 'C', 'delta': long_call['delta']}
            ],
            credit=credit,
            max_loss=max_loss,
            probability=pop,
            score=score,
            rationale=f"Low volatility regime, {range_pct:.1%} expected range"
        )
```

---

## 3. Algorithm Rules (from v1.1)

### 3.1 Data Quality Filters
```python
QUALITY_FILTERS = {
    'max_spread': 5.0,      # Drop if bid-ask > $5
    'min_open_interest': 100,  # Drop if OI < 100
    'min_volume': 1,        # Must have traded today
    'max_iv_spread': 0.10,  # Drop if IV spread > 10%
}
```

### 3.2 Strategy Selection Matrix

| Market Condition | Strategy | Entry Criteria | Strike Selection |
|-----------------|----------|----------------|------------------|
| **Range < 0.6%** | Iron Condor | ATR×3 < 0.6% spot | Short: 10-15Δ, Long: 5-7Δ |
| **At GEX Flip** | Butterfly | \|Spot-GEX\| < 1% | Center: GEX flip ±1 strike |
| **Trend > 0.4%** | Vertical | (Spot-GEX)/Spot > 0.4% | Short: 20-25Δ, Long: 10-15Δ |

### 3.3 Order Execution Logic
```python
ORDER_RULES = {
    'initial_edge': 2,      # Start at mid ± 2 ticks
    'wait_time': 30,        # Wait 30s before widening
    'widen_increment': 1,   # Widen by 1 tick
    'max_attempts': 5,      # Max 5 attempts
    'min_fill_size': 0.8,   # Accept 80% partial fills
}
```

---

## 4. Development Timeline (14 Trading Days)

### Phase M0: Infrastructure (Day 1)
```bash
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    
  postgres:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: magic8clone
      POSTGRES_USER: quant
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  data_collector:
    build: ./services/data_collector
    environment:
      IB_HOST: host.docker.internal
      IB_PORT: 7497
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql+asyncpg://quant:${DB_PASSWORD}@postgres/magic8clone
    depends_on:
      - redis
      - postgres
      
  greeks_engine:
    build: ./services/greeks_engine
    environment:
      REDIS_URL: redis://redis:6379
      USE_GPU: ${USE_GPU:-false}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
              
  combo_selector:
    build: ./services/combo_selector
    environment:
      REDIS_URL: redis://redis:6379
    depends_on:
      - greeks_engine
      
  order_manager:
    build: ./services/order_manager
    environment:
      IB_HOST: host.docker.internal
      IB_PORT: 7497
      REDIS_URL: redis://redis:6379
      DRY_RUN: ${DRY_RUN:-true}
      
  dashboard:
    build: ./services/dashboard
    ports:
      - "8501:8501"
    environment:
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://quant:${DB_PASSWORD}@postgres/magic8clone

volumes:
  redis_data:
  postgres_data:
```

### Phase M1: Data Collection (Days 2-3)
- Implement IB connection with reconnect logic
- Create option chain snapshots every 5 min
- Store in PostgreSQL with TimescaleDB
- Verify data quality filters

### Phase M2: Greeks & GEX (Days 4-5)
- Integrate py_vollib_vectorized
- Adapt SPX-Gamma-Exposure for real-time
- Benchmark CPU vs GPU performance
- Cache calculations in Redis

### Phase M3: Strategy Selection (Days 6-8)
- Implement rule-based selector
- Add ATR calculation
- Create combo formation logic
- Generate formatted recommendations

### Phase M4: Execution & Monitoring (Days 9-11)
- Build order manager with IB execution
- Implement order retry logic
- Create Streamlit dashboard
- Add Slack notifications

### Phase M5: Testing & Go-Live (Days 12-14)
- Historical backtesting with optopsy
- Shadow-live comparison
- Performance optimization
- Paper trading activation

---

## 5. Testing Strategy

### 5.1 Unit Tests
```python
# tests/test_combo_selector.py
import pytest
from services.combo_selector import ComboSelectorService

@pytest.fixture
def mock_chain_data():
    # Create realistic option chain
    pass

def test_iron_condor_selection(mock_chain_data):
    selector = ComboSelectorService({})
    # Set ATR to trigger IC
    recommendations = selector.select_combos(
        mock_chain_data, 
        mock_greeks,
        mock_gex
    )
    assert recommendations[0].strategy == 'iron_condor'
    assert 0.10 <= abs(recommendations[0].legs[0]['delta']) <= 0.15
```

### 5.2 Integration Tests
```python
# tests/test_integration.py
@pytest.mark.integration
async def test_end_to_end_flow():
    # Start all services
    # Inject test data
    # Verify recommendation output
    # Check execution flow
    pass
```

### 5.3 Shadow-Live Testing
```python
# services/shadow_comparator/main.py
class ShadowComparator:
    """Compare our predictions with Magic8 actuals"""
    
    async def compare_predictions(self, our_pred, magic8_pred):
        metrics = {
            'direction_match': our_pred['trend'] == magic8_pred['trend'],
            'strike_diff': abs(our_pred['strikes'] - magic8_pred['strikes']),
            'credit_diff': abs(our_pred['credit'] - magic8_pred['credit']),
            'strategy_match': our_pred['strategy'] == magic8_pred['strategy']
        }
        
        # Store comparison
        await self.store_comparison(metrics)
        
        # Alert on major divergence
        if metrics['strike_diff'] > 10:
            await self.alert_divergence(metrics)
```

### 5.4 Performance KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **End-to-end latency** | < 30s | Prometheus histogram |
| **Fill ratio** | ≥ 85% | Orders filled / submitted |
| **Queue delay** | < 1s | Redis stream lag |
| **Prediction accuracy** | > 65% | Direction correctness |
| **System uptime** | > 99.5% | Health check endpoint |

---

## 6. Production Deployment

### 6.1 AWS Infrastructure
```terraform
# infrastructure/main.tf
resource "aws_ecs_cluster" "magic8clone" {
  name = "magic8clone-prod"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "services" {
  for_each = toset(["data_collector", "greeks_engine", 
                    "combo_selector", "order_manager"])
  
  name            = each.key
  cluster         = aws_ecs_cluster.magic8clone.id
  task_definition = aws_ecs_task_definition.services[each.key].arn
  desired_count   = 1
  
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
}
```

### 6.2 Monitoring Stack
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'services'
    static_configs:
      - targets: 
        - data_collector:9090
        - greeks_engine:9090
        - combo_selector:9090
        - order_manager:9090
        
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
        
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:9187']
```

---

## 7. Stage 2 Enhancements

### 7.1 Machine Learning Integration (Weeks 3-4)
- Port iron-condor LSTM to PyTorch Lightning
- Create feature store in PostgreSQL
- A/B test ML vs rules-based
- Target: +10% accuracy improvement

### 7.2 Multi-Broker Support (Week 5)
- Abstract broker interface
- Add pyetrade for E*TRADE
- Implement smart order routing
- Compare fill quality

### 7.3 Platform Migration Path (Week 6+)
```python
# Trigger conditions for Rust migration
MIGRATION_TRIGGERS = {
    'daily_trades': 200,      # > 200 trades/day
    'latency_p99': 100,       # > 100ms p99 latency
    'message_rate': 10000,    # > 10k messages/sec
}
```

---

## 8. Quick Start Commands

```bash
# Clone and setup
git clone <repo>
cd magic8clone
cp .env.example .env

# Start development environment
docker-compose up -d

# Run tests
docker-compose run tests pytest

# Deploy single service
docker-compose up -d combo_selector

# View logs
docker-compose logs -f combo_selector

# Access dashboard
open http://localhost:8501

# Start paper trading
docker-compose run order_manager python -m services.order_manager.main --paper
```

---

## 9. Key Differentiators from v1.0

1. **Microservice architecture** - Better scalability and maintenance
2. **Redis streams** - Reliable message delivery with replay
3. **Shadow-live testing** - Validate against real Magic8
4. **Specific thresholds** - Concrete rules (0.6%, 10-15Δ, etc.)
5. **Performance KPIs** - Measurable targets
6. **GPU cost gating** - Use GPU only when economical
7. **TimescaleDB** - Optimized for time-series data

---

## 10. Risk Management

### 10.1 Circuit Breakers
```python
CIRCUIT_BREAKERS = {
    'max_daily_loss': 5000,      # Stop if -$5k
    'max_position_size': 10,      # Max 10 contracts
    'max_concurrent_orders': 5,   # Max 5 open orders
    'min_account_balance': 25000, # PDT requirement
}
```

### 10.2 Operational Risks
- IB connection loss → Auto-reconnect with exponential backoff
- Redis failure → Local queue fallback
- PostgreSQL down → Read from Redis cache
- Service crash → Docker auto-restart policy

---

## References & Resources

### Documentation
- [IB API Gateway Setup](https://interactivebrokers.github.io/tws-api/initial_setup.html)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [TimescaleDB Hypertables](https://docs.timescale.com/latest/using-timescaledb/hypertables)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)

### Community
- Magic8Clone Slack: `#magic8clone-dev`
- Weekly sync: Thursdays 3pm ET
- Issue tracker: GitHub Issues

---

**Version**: 2.0  
**Updated**: June 7, 2025  
**Maintainer**: @quant_dev  
**License**: MIT (except GPL-3 components)

*This refined plan incorporates microservice architecture, specific algorithmic thresholds, and production-grade monitoring while maintaining the detailed implementation guidance from the original plan.*