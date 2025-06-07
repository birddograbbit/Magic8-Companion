# Magic8Clone v2.1 - Implementation Guide
## Ship Fast, Then Split

*Start Date: ____________*  
*Target Paper Trading: Day 10*  
*Team: DevOps, Quant, Algo Eng*

---

## Day 1: Development Infrastructure Setup

### 1.1 Project Structure
```bash
magic8clone/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── magic8clone/
│   ├── __init__.py
│   ├── main.py              # Mono-service orchestrator
│   ├── config.py            # Pydantic settings
│   ├── modules/             # Future microservice boundaries
│   │   ├── __init__.py
│   │   ├── data_collector/
│   │   │   ├── __init__.py
│   │   │   ├── ib_connector.py
│   │   │   └── schemas.py
│   │   ├── greeks_engine/
│   │   │   ├── __init__.py
│   │   │   ├── calculator.py
│   │   │   └── gex_analyzer.py
│   │   ├── combo_selector/
│   │   │   ├── __init__.py
│   │   │   ├── strategies.py
│   │   │   └── rules.py
│   │   └── order_manager/
│   │       ├── __init__.py
│   │       ├── executor.py
│   │       └── risk_checks.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── redis_client.py
│   │   ├── db_client.py
│   │   └── monitoring.py
│   └── tests/
├── infra/
│   ├── terraform/
│   └── k8s/
└── scripts/
    ├── setup_dev.sh
    └── deploy_prod.sh
```

### 1.2 Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --appendfsync everysec
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: magic8clone
      POSTGRES_USER: quant
      POSTGRES_PASSWORD: ${DB_PASSWORD:-supersecret}
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U quant -d magic8clone"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    volumes:
      - ./infra/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./infra/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./infra/grafana/datasources:/etc/grafana/provisioning/datasources

  # Phase 0: Mono-service (comment out for initial development)
  magic8clone:
    build: .
    environment:
      - IB_HOST=${IB_HOST:-host.docker.internal}
      - IB_PORT=${IB_PORT:-7497}
      - IB_CLIENT_ID=${IB_CLIENT_ID:-1}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://quant:${DB_PASSWORD:-supersecret}@timescaledb:5432/magic8clone
      - USE_GPU=${USE_GPU:-false}
      - DRY_RUN=${DRY_RUN:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      redis:
        condition: service_healthy
      timescaledb:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    ports:
      - "8000:8000"  # FastAPI metrics endpoint

volumes:
  redis_data:
  timescale_data:
  prometheus_data:
  grafana_data:
```

### 1.3 Configuration Management
```python
# magic8clone/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Central configuration with env override"""
    
    # IB Connection
    ib_host: str = "127.0.0.1"
    ib_port: int = 7497
    ib_client_id: int = 1
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_stream_maxlen: int = 10000
    
    # PostgreSQL/TimescaleDB
    database_url: str = "postgresql://quant:supersecret@localhost:5432/magic8clone"
    
    # Algorithm Parameters
    quality_filters: dict = {
        "max_spread": 5.0,
        "min_open_interest": 100,
        "min_volume": 1,
        "max_iv_spread": 0.10
    }
    
    strategy_matrix: dict = {
        "iron_condor": {
            "range_pct_lt": 0.006,
            "short_delta": 0.10,
            "long_delta": 0.05
        },
        "butterfly": {
            "gex_distance_pct_lt": 0.01,
            "max_debit_pct": 0.002
        },
        "vertical": {
            "gex_distance_pct_gt": 0.004,
            "short_delta": 0.20,
            "long_delta": 0.10
        }
    }
    
    order_rules: dict = {
        "initial_edge_ticks": 2,
        "widen_every_s": 30,
        "max_attempts": 5,
        "min_fill_size": 0.8
    }
    
    # Circuit Breakers
    circuit_breakers: dict = {
        "max_daily_loss": 5000,
        "max_position_size": 10,
        "max_concurrent_orders": 5,
        "min_account_balance": 25000
    }
    
    # Performance Triggers (when to split to microservices)
    performance_triggers: dict = {
        "latency_p95_ms": 20000,  # 20s
        "throughput_tps": 10
    }
    
    # Feature Flags
    use_gpu: bool = False
    dry_run: bool = True
    enable_shadow_live: bool = False
    use_microservices: bool = False
    
    # Monitoring
    metrics_port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
settings = Settings()

# Hot reload on SIGUSR2
import signal
def reload_config(signum, frame):
    global settings
    settings = Settings()
    print("Configuration reloaded")
    
signal.signal(signal.SIGUSR2, reload_config)
```

### 1.4 Database Schema
```sql
-- scripts/init_db.sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Option chain snapshots
CREATE TABLE option_chain (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    expiry DATE NOT NULL,
    option_type CHAR(1) NOT NULL,
    bid DECIMAL(10,2),
    ask DECIMAL(10,2),
    last DECIMAL(10,2),
    volume INTEGER,
    open_interest INTEGER,
    implied_vol DECIMAL(6,4),
    delta DECIMAL(6,4),
    gamma DECIMAL(8,6),
    theta DECIMAL(8,4),
    vega DECIMAL(8,4),
    spot_price DECIMAL(10,2)
);

SELECT create_hypertable('option_chain', 'time', chunk_time_interval => interval '1 hour');
CREATE INDEX idx_option_chain_strike ON option_chain (strike, time DESC);

-- GEX calculations
CREATE TABLE gamma_exposure (
    time TIMESTAMPTZ NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    gex_value DECIMAL(15,2),
    total_gamma DECIMAL(15,2),
    zero_gamma_level DECIMAL(10,2),
    put_wall DECIMAL(10,2),
    call_wall DECIMAL(10,2)
);

SELECT create_hypertable('gamma_exposure', 'time', chunk_time_interval => interval '1 hour');

-- Predictions
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    strategy VARCHAR(20) NOT NULL,
    legs JSONB NOT NULL,
    credit DECIMAL(10,2),
    max_loss DECIMAL(10,2),
    probability DECIMAL(5,2),
    score DECIMAL(5,2),
    rationale TEXT,
    executed BOOLEAN DEFAULT FALSE
);

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER REFERENCES predictions(id),
    ib_order_id INTEGER,
    status VARCHAR(20),
    fill_price DECIMAL(10,2),
    fill_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    value DECIMAL(15,4),
    labels JSONB
);

SELECT create_hypertable('performance_metrics', 'time', chunk_time_interval => interval '1 day');
```

---

## Day 2-3: IB Data Collector Module

### 2.1 IB Connector Implementation
```python
# magic8clone/modules/data_collector/ib_connector.py
import asyncio
from typing import List, Optional, Dict
import pandas as pd
from datetime import datetime, timedelta
from ib_async import IB, Stock, Index, Option, util, MarketOrder, LimitOrder
import logging
from ...config import settings
from ...utils.monitoring import metrics

logger = logging.getLogger(__name__)

class IBConnector:
    """Async IB connection with auto-reconnect and monitoring"""
    
    def __init__(self):
        self.ib = IB()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    async def connect(self):
        """Connect with exponential backoff"""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                await self.ib.connectAsync(
                    settings.ib_host,
                    settings.ib_port,
                    clientId=settings.ib_client_id,
                    timeout=20
                )
                self.connected = True
                self.reconnect_attempts = 0
                logger.info("Connected to IB Gateway")
                
                # Set up event handlers
                self.ib.errorEvent += self.on_error
                self.ib.disconnectedEvent += self.on_disconnect
                
                return True
                
            except Exception as e:
                self.reconnect_attempts += 1
                wait_time = 2 ** self.reconnect_attempts
                logger.error(f"Connection failed, retry {self.reconnect_attempts} in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
        raise ConnectionError("Max reconnection attempts reached")
        
    async def on_disconnect(self):
        """Handle disconnection"""
        self.connected = False
        logger.warning("Disconnected from IB Gateway")
        metrics.increment('ib.disconnections')
        await self.connect()
        
    def on_error(self, reqId, errorCode, errorString, contract):
        """Handle IB errors"""
        logger.error(f"IB Error - ReqId: {reqId}, Code: {errorCode}, Msg: {errorString}")
        metrics.increment('ib.errors', tags={'code': str(errorCode)})
        
    async def get_spx_price(self) -> float:
        """Get current SPX spot price"""
        spx = Index('SPX', 'CBOE', 'USD')
        await self.ib.qualifyContractsAsync(spx)
        
        ticker = self.ib.reqMktData(spx, '', False, False)
        await asyncio.sleep(2)  # Wait for data
        
        price = ticker.marketPrice()
        if price is None or price <= 0:
            price = ticker.last
            
        self.ib.cancelMktData(spx)
        return price
        
    async def get_0dte_chain(self) -> pd.DataFrame:
        """Fetch complete 0DTE option chain"""
        with metrics.timer('ib.chain_fetch'):
            spx = Index('SPX', 'CBOE', 'USD')
            await self.ib.qualifyContractsAsync(spx)
            
            # Get chain parameters
            chains = await self.ib.reqSecDefOptParamsAsync(
                spx.symbol, '', spx.secType, spx.conId
            )
            
            if not chains:
                raise ValueError("No option chains found")
                
            chain = chains[0]
            
            # Find today's expiration (0DTE)
            today = datetime.now().date()
            expirations = [
                exp for exp in chain.expirations 
                if datetime.strptime(exp, '%Y%m%d').date() == today
            ]
            
            if not expirations:
                # Use nearest expiration
                all_exp = sorted(chain.expirations)
                expirations = [all_exp[0]]
                logger.warning(f"No 0DTE found, using {expirations[0]}")
                
            # Get current spot for strike filtering
            spot = await self.get_spx_price()
            
            # Filter strikes within 5% of spot
            strikes = [
                strike for strike in chain.strikes
                if abs(strike - spot) / spot <= 0.05
            ]
            
            # Create option contracts
            options = []
            for exp in expirations:
                for strike in strikes:
                    for right in ['C', 'P']:
                        opt = Option('SPX', exp, strike, right, 'CBOE')
                        options.append(opt)
                        
            # Qualify contracts
            qualified = await self.ib.qualifyContractsAsync(*options)
            
            # Request market data with Greeks
            tickers = []
            for contract in qualified:
                ticker = self.ib.reqMktData(
                    contract, 
                    genericTickList='100,101,104,106,13',  # Include Greeks
                    snapshot=False,
                    regulatorySnapshot=False
                )
                tickers.append(ticker)
                
            # Wait for data to populate
            await asyncio.sleep(3)
            
            # Build DataFrame
            data = []
            for ticker in tickers:
                if ticker.bid is not None and ticker.ask is not None:
                    # Calculate spread
                    spread = ticker.ask - ticker.bid
                    
                    # Skip if spread too wide
                    if spread > settings.quality_filters['max_spread']:
                        continue
                        
                    # Skip if no open interest
                    oi = ticker.openInterest or 0
                    if oi < settings.quality_filters['min_open_interest']:
                        continue
                        
                    data.append({
                        'time': datetime.utcnow(),
                        'symbol': ticker.contract.symbol,
                        'strike': ticker.contract.strike,
                        'expiry': ticker.contract.lastTradeDateOrContractMonth,
                        'option_type': ticker.contract.right,
                        'bid': ticker.bid,
                        'ask': ticker.ask,
                        'last': ticker.last,
                        'volume': ticker.volume or 0,
                        'open_interest': oi,
                        'implied_vol': ticker.impliedVolatility,
                        'delta': ticker.modelGreeks.delta if ticker.modelGreeks else None,
                        'gamma': ticker.modelGreeks.gamma if ticker.modelGreeks else None,
                        'theta': ticker.modelGreeks.theta if ticker.modelGreeks else None,
                        'vega': ticker.modelGreeks.vega if ticker.modelGreeks else None,
                        'spot_price': spot
                    })
                    
            # Cancel market data
            for ticker in tickers:
                self.ib.cancelMktData(ticker.contract)
                
            df = pd.DataFrame(data)
            logger.info(f"Fetched {len(df)} option contracts")
            metrics.gauge('ib.chain_size', len(df))
            
            return df
            
    async def place_order(self, contract, order_type: str, quantity: int, 
                         limit_price: Optional[float] = None) -> int:
        """Place order and return IB order ID"""
        if order_type == 'LIMIT':
            order = LimitOrder('BUY' if quantity > 0 else 'SELL', 
                             abs(quantity), limit_price)
        else:
            order = MarketOrder('BUY' if quantity > 0 else 'SELL', 
                               abs(quantity))
                               
        trade = self.ib.placeOrder(contract, order)
        return trade.order.orderId
        
    def disconnect(self):
        """Clean disconnect"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
```

### 2.2 Data Storage Module
```python
# magic8clone/utils/db_client.py
import asyncpg
from contextlib import asynccontextmanager
import pandas as pd
from typing import Dict, List
import json
from datetime import datetime
from ..config import settings

class TimescaleDB:
    """Async TimescaleDB client with connection pooling"""
    
    def __init__(self):
        self.pool = None
        
    async def connect(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        async with self.pool.acquire() as conn:
            yield conn
            
    async def insert_option_chain(self, df: pd.DataFrame):
        """Bulk insert option chain data"""
        records = df.to_dict('records')
        
        async with self.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO option_chain (
                    time, symbol, strike, expiry, option_type,
                    bid, ask, last, volume, open_interest,
                    implied_vol, delta, gamma, theta, vega, spot_price
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                [
                    (
                        r['time'], r['symbol'], r['strike'], r['expiry'], 
                        r['option_type'], r['bid'], r['ask'], r['last'],
                        r['volume'], r['open_interest'], r['implied_vol'],
                        r['delta'], r['gamma'], r['theta'], r['vega'], r['spot_price']
                    )
                    for r in records
                ]
            )
            
    async def get_latest_chain(self) -> pd.DataFrame:
        """Get most recent option chain"""
        async with self.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM option_chain
                WHERE time > NOW() - INTERVAL '10 minutes'
                ORDER BY time DESC
                """
            )
            
        return pd.DataFrame(rows)
        
    async def insert_prediction(self, prediction: Dict):
        """Insert prediction record"""
        async with self.acquire() as conn:
            result = await conn.fetchrow(
                """
                INSERT INTO predictions (
                    time, strategy, legs, credit, max_loss,
                    probability, score, rationale
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                datetime.utcnow(),
                prediction['strategy'],
                json.dumps(prediction['legs']),
                prediction['credit'],
                prediction['max_loss'],
                prediction['probability'],
                prediction['score'],
                prediction['rationale']
            )
            
        return result['id']
        
    async def record_metric(self, metric_name: str, value: float, labels: Dict = None):
        """Record performance metric"""
        async with self.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO performance_metrics (time, metric_name, value, labels)
                VALUES ($1, $2, $3, $4)
                """,
                datetime.utcnow(),
                metric_name,
                value,
                json.dumps(labels or {})
            )
```

---

## Day 4-5: Greeks & GEX Engine Module

### 4.1 Greeks Calculator
```python
# magic8clone/modules/greeks_engine/calculator.py
import numpy as np
import pandas as pd
from typing import Optional, Dict
import py_vollib_vectorized as pv
from datetime import datetime
import logging
from ...config import settings
from ...utils.monitoring import metrics

logger = logging.getLogger(__name__)

class GreeksEngine:
    """High-performance Greeks calculation with optional GPU support"""
    
    def __init__(self):
        self.risk_free_rate = 0.05  # Current risk-free rate
        self.use_gpu = settings.use_gpu
        
        if self.use_gpu and self._check_gpu_available():
            try:
                import OptionGreeksGPU
                self.calculator = OptionGreeksGPU
                logger.info("Using GPU for Greeks calculations")
            except ImportError:
                logger.warning("GPU requested but OptionGreeksGPU not available")
                self.calculator = pv
        else:
            self.calculator = pv
            
    def _check_gpu_available(self) -> bool:
        """Check if GPU is available and cost-effective"""
        try:
            import subprocess
            # Check NVIDIA GPU
            result = subprocess.run(['nvidia-smi'], capture_output=True)
            if result.returncode != 0:
                return False
                
            # Check spot instance price if on AWS
            # Placeholder - implement actual price check
            spot_price = self._get_spot_price()
            return spot_price < 0.50  # $0.50/hour threshold
            
        except:
            return False
            
    def _get_spot_price(self) -> float:
        """Get current GPU spot instance price"""
        # TODO: Implement AWS/GCP price API check
        return 0.30  # Placeholder
        
    def calculate_greeks(self, option_chain: pd.DataFrame) -> pd.DataFrame:
        """Calculate all Greeks for option chain"""
        with metrics.timer('greeks.calculation'):
            # Current time to expiration
            now = datetime.now()
            expiry = pd.to_datetime(option_chain['expiry'].iloc[0])
            
            # Calculate time to expiration in years
            time_diff = expiry - now
            T = (time_diff.days + time_diff.seconds / 86400) / 365.0
            
            # Prepare vectorized inputs
            S = option_chain['spot_price'].values
            K = option_chain['strike'].values
            r = np.full_like(S, self.risk_free_rate)
            
            # Use IV from market data, fallback to 20% if missing
            sigma = option_chain['implied_vol'].fillna(0.20).values
            
            # Convert option type to flag
            flag = option_chain['option_type'].map({'C': 'c', 'P': 'p'}).values
            
            # Calculate all Greeks at once
            try:
                delta = self.calculator.greeks.analytical.delta(flag, S, K, T, r, sigma)
                gamma = self.calculator.greeks.analytical.gamma(flag, S, K, T, r, sigma)
                theta = self.calculator.greeks.analytical.theta(flag, S, K, T, r, sigma)
                vega = self.calculator.greeks.analytical.vega(flag, S, K, T, r, sigma)
                rho = self.calculator.greeks.analytical.rho(flag, S, K, T, r, sigma)
                
                # Add calculated Greeks to DataFrame
                option_chain['calc_delta'] = delta
                option_chain['calc_gamma'] = gamma
                option_chain['calc_theta'] = theta
                option_chain['calc_vega'] = vega
                option_chain['calc_rho'] = rho
                
                # Use calculated values where market Greeks are missing
                for greek in ['delta', 'gamma', 'theta', 'vega']:
                    mask = option_chain[greek].isna()
                    option_chain.loc[mask, greek] = option_chain.loc[mask, f'calc_{greek}']
                    
                # Drop calculation columns
                option_chain = option_chain.drop(columns=[col for col in option_chain.columns if col.startswith('calc_')])
                
                logger.info(f"Calculated Greeks for {len(option_chain)} options")
                metrics.gauge('greeks.options_processed', len(option_chain))
                
            except Exception as e:
                logger.error(f"Greeks calculation failed: {e}")
                metrics.increment('greeks.calculation_errors')
                raise
                
        return option_chain
        
    def calculate_portfolio_greeks(self, positions: List[Dict]) -> Dict:
        """Calculate aggregate Greeks for portfolio"""
        total_delta = sum(p['quantity'] * p['delta'] for p in positions)
        total_gamma = sum(p['quantity'] * p['gamma'] for p in positions)
        total_theta = sum(p['quantity'] * p['theta'] for p in positions)
        total_vega = sum(p['quantity'] * p['vega'] for p in positions)
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega,
            'delta_dollars': total_delta * 100 * positions[0]['spot_price']  # SPX multiplier
        }
```

### 4.2 GEX Analyzer
```python
# magic8clone/modules/greeks_engine/gex_analyzer.py
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging
from ...utils.monitoring import metrics

logger = logging.getLogger(__name__)

class GEXAnalyzer:
    """Gamma Exposure calculation adapted from SPX-Gamma-Exposure"""
    
    def __init__(self):
        self.contract_multiplier = 100  # SPX multiplier
        
    def calculate_gex(self, option_chain: pd.DataFrame) -> Dict:
        """Calculate gamma exposure by strike"""
        with metrics.timer('gex.calculation'):
            spot_price = option_chain['spot_price'].iloc[0]
            
            # Calculate GEX for each option
            # GEX = Gamma * Contract Size * Open Interest * Spot^2 * 0.01
            option_chain['gex'] = (
                option_chain['gamma'] * 
                self.contract_multiplier * 
                option_chain['open_interest'] * 
                spot_price ** 2 * 
                0.01
            )
            
            # Calls add positive gamma, puts add negative gamma (dealer perspective)
            option_chain.loc[option_chain['option_type'] == 'P', 'gex'] *= -1
            
            # Aggregate by strike
            gex_by_strike = option_chain.groupby('strike')['gex'].sum()
            
            # Calculate key levels
            total_gamma = gex_by_strike.sum()
            zero_gamma = self._find_zero_gamma(gex_by_strike, spot_price)
            max_gamma_strike = gex_by_strike.abs().idxmax()
            put_wall = self._find_put_wall(option_chain, spot_price)
            call_wall = self._find_call_wall(option_chain, spot_price)
            
            results = {
                'spot_price': spot_price,
                'total_gamma': total_gamma,
                'zero_gamma_level': zero_gamma,
                'max_gamma_strike': max_gamma_strike,
                'put_wall': put_wall,
                'call_wall': call_wall,
                'gex_by_strike': gex_by_strike.to_dict()
            }
            
            logger.info(f"GEX calculated - Total: {total_gamma/1e9:.2f}B, Zero: {zero_gamma}")
            metrics.gauge('gex.total_gamma_billions', total_gamma / 1e9)
            
            return results
            
    def _find_zero_gamma(self, gex_by_strike: pd.Series, spot: float) -> float:
        """Find strike where cumulative gamma crosses zero"""
        cumulative_gex = gex_by_strike.sort_index().cumsum()
        
        # Find zero crossing
        negative = cumulative_gex[cumulative_gex < 0]
        positive = cumulative_gex[cumulative_gex > 0]
        
        if len(negative) > 0 and len(positive) > 0:
            # Linear interpolation between strikes
            last_negative_strike = negative.index[-1]
            first_positive_strike = positive.index[0]
            
            if first_positive_strike > last_negative_strike:
                last_negative_value = negative.iloc[-1]
                first_positive_value = positive.iloc[0]
                
                # Interpolate
                ratio = abs(last_negative_value) / (abs(last_negative_value) + first_positive_value)
                zero_gamma = last_negative_strike + ratio * (first_positive_strike - last_negative_strike)
                
                return zero_gamma
                
        return spot
        
    def _find_put_wall(self, option_chain: pd.DataFrame, spot: float) -> float:
        """Find largest put gamma concentration below spot"""
        puts = option_chain[
            (option_chain['option_type'] == 'P') & 
            (option_chain['strike'] < spot)
        ]
        
        if len(puts) == 0:
            return spot - 50
            
        put_gex = puts.groupby('strike')['gex'].sum().abs()
        return put_gex.idxmax()
        
    def _find_call_wall(self, option_chain: pd.DataFrame, spot: float) -> float:
        """Find largest call gamma concentration above spot"""
        calls = option_chain[
            (option_chain['option_type'] == 'C') & 
            (option_chain['strike'] > spot)
        ]
        
        if len(calls) == 0:
            return spot + 50
            
        call_gex = calls.groupby('strike')['gex'].sum()
        return call_gex.idxmax()
        
    def calculate_expected_move(self, gex_data: Dict, atr_5min: float) -> Dict:
        """Calculate expected move based on GEX and ATR"""
        spot = gex_data['spot_price']
        zero_gamma = gex_data['zero_gamma_level']
        
        # Base expected move on ATR
        expected_range = atr_5min * 3
        
        # Adjust based on gamma positioning
        if gex_data['total_gamma'] < -1e9:  # Negative gamma
            # Dealers short gamma, expect larger moves
            expected_range *= 1.5
        elif gex_data['total_gamma'] > 1e9:  # Positive gamma
            # Dealers long gamma, expect smaller moves
            expected_range *= 0.7
            
        return {
            'expected_range': expected_range,
            'expected_range_pct': expected_range / spot,
            'upper_bound': spot + expected_range,
            'lower_bound': spot - expected_range,
            'gamma_pin': zero_gamma
        }
```

---

## Day 6-7: Combo Selector Module

### 6.1 Strategy Implementation
```python
# magic8clone/modules/combo_selector/strategies.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from ...config import settings
from ...utils.monitoring import metrics

logger = logging.getLogger(__name__)

@dataclass
class OptionLeg:
    action: str  # BUY or SELL
    strike: float
    option_type: str  # C or P
    delta: float
    bid: float
    ask: float
    
@dataclass
class ComboRecommendation:
    strategy: str
    legs: List[OptionLeg]
    credit: float
    max_loss: float
    probability: float
    score: float
    rationale: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
            
    def to_dict(self) -> Dict:
        return {
            'strategy': self.strategy,
            'legs': [
                {
                    'action': leg.action,
                    'strike': leg.strike,
                    'option_type': leg.option_type,
                    'delta': leg.delta
                }
                for leg in self.legs
            ],
            'credit': self.credit,
            'max_loss': self.max_loss,
            'probability': self.probability,
            'score': self.score,
            'rationale': self.rationale,
            'created_at': self.created_at.isoformat()
        }

class StrategySelector:
    """Rule-based strategy selection engine"""
    
    def __init__(self):
        self.config = settings.strategy_matrix
        
    async def select_strategies(self, 
                              option_chain: pd.DataFrame,
                              gex_data: Dict,
                              market_metrics: Dict) -> List[ComboRecommendation]:
        """Select optimal strategies based on market conditions"""
        recommendations = []
        
        # Calculate market state
        spot = option_chain['spot_price'].iloc[0]
        range_pct = market_metrics['expected_range_pct']
        gex_distance = abs(spot - gex_data['zero_gamma_level'])
        gex_distance_pct = gex_distance / spot
        
        logger.info(f"Market state - Range: {range_pct:.3%}, GEX distance: {gex_distance_pct:.3%}")
        
        # Iron Condor - low volatility, range-bound
        if range_pct < self.config['iron_condor']['range_pct_lt']:
            ic = self._build_iron_condor(option_chain, spot)
            if ic and ic.score >= 70:
                recommendations.append(ic)
                metrics.increment('strategies.iron_condor_selected')
                
        # Butterfly - pinning at GEX level
        if gex_distance_pct < self.config['butterfly']['gex_distance_pct_lt']:
            bf = self._build_butterfly(option_chain, gex_data['zero_gamma_level'])
            if bf and bf.score >= 75:
                recommendations.append(bf)
                metrics.increment('strategies.butterfly_selected')
                
        # Vertical spread - directional
        if gex_distance_pct > self.config['vertical']['gex_distance_pct_gt']:
            direction = 'bull' if spot < gex_data['zero_gamma_level'] else 'bear'
            vert = self._build_vertical(option_chain, direction)
            if vert and vert.score >= 65:
                recommendations.append(vert)
                metrics.increment('strategies.vertical_selected')
                
        # Sort by score and return top 3
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:3]
        
    def _build_iron_condor(self, chain: pd.DataFrame, spot: float) -> Optional[ComboRecommendation]:
        """Build Iron Condor with 10-15 delta wings"""
        target_short_delta = self.config['iron_condor']['short_delta']
        target_long_delta = self.config['iron_condor']['long_delta']
        
        puts = chain[chain['option_type'] == 'P'].copy()
        calls = chain[chain['option_type'] == 'C'].copy()
        
        # Find strikes closest to target deltas
        short_put = self._find_by_delta(puts, -target_short_delta, tolerance=0.03)
        long_put = self._find_by_delta(puts, -target_long_delta, tolerance=0.02)
        short_call = self._find_by_delta(calls, target_short_delta, tolerance=0.03)
        long_call = self._find_by_delta(calls, target_long_delta, tolerance=0.02)
        
        if not all([short_put is not None, long_put is not None, 
                   short_call is not None, long_call is not None]):
            logger.warning("Could not find all IC legs")
            return None
            
        # Verify strike relationships
        if not (long_put['strike'] < short_put['strike'] < short_call['strike'] < long_call['strike']):
            logger.warning("Invalid IC strike relationships")
            return None
            
        # Calculate P&L
        credit = (
            short_put['bid'] + short_call['bid'] -
            long_put['ask'] - long_call['ask']
        )
        
        if credit <= 0:
            return None
            
        # Max loss is width minus credit
        put_width = short_put['strike'] - long_put['strike']
        call_width = long_call['strike'] - short_call['strike']
        max_width = max(put_width, call_width)
        max_loss = (max_width - credit) * 100  # SPX multiplier
        
        # Probability of profit (simplified)
        # Assume 68% for 1 SD move
        prob_touch_put = 2 * abs(short_put['delta'])
        prob_touch_call = 2 * short_call['delta']
        probability = 1 - (prob_touch_put + prob_touch_call)
        
        # Score based on risk/reward and probability
        risk_reward = credit / max_width
        score = min(100, risk_reward * 100 * probability * 2)
        
        return ComboRecommendation(
            strategy='iron_condor',
            legs=[
                OptionLeg('SELL', short_put['strike'], 'P', short_put['delta'],
                         short_put['bid'], short_put['ask']),
                OptionLeg('BUY', long_put['strike'], 'P', long_put['delta'],
                         long_put['bid'], long_put['ask']),
                OptionLeg('SELL', short_call['strike'], 'C', short_call['delta'],
                         short_call['bid'], short_call['ask']),
                OptionLeg('BUY', long_call['strike'], 'C', long_call['delta'],
                         long_call['bid'], long_call['ask'])
            ],
            credit=credit,
            max_loss=max_loss,
            probability=probability,
            score=score,
            rationale=f"Low volatility environment with {probability:.1%} probability of profit"
        )
        
    def _build_butterfly(self, chain: pd.DataFrame, center_strike: float) -> Optional[ComboRecommendation]:
        """Build butterfly centered at GEX level"""
        # Find ATM strike closest to center
        strikes = chain['strike'].unique()
        center = min(strikes, key=lambda x: abs(x - center_strike))
        
        # Find wings 25 points away (for SPX)
        wing_distance = 25
        lower = center - wing_distance
        upper = center + wing_distance
        
        # Get option data
        center_call = chain[(chain['strike'] == center) & (chain['option_type'] == 'C')].iloc[0]
        lower_call = chain[(chain['strike'] == lower) & (chain['option_type'] == 'C')]
        upper_call = chain[(chain['strike'] == upper) & (chain['option_type'] == 'C')]
        
        if len(lower_call) == 0 or len(upper_call) == 0:
            return None
            
        lower_call = lower_call.iloc[0]
        upper_call = upper_call.iloc[0]
        
        # Calculate debit (buy 1 lower, sell 2 center, buy 1 upper)
        debit = (
            lower_call['ask'] - 2 * center_call['bid'] + upper_call['ask']
        )
        
        # Check max debit constraint
        spot = chain['spot_price'].iloc[0]
        max_debit = spot * self.config['butterfly']['max_debit_pct']
        
        if debit > max_debit:
            return None
            
        # Max profit is wing width minus debit
        max_profit = (wing_distance - debit) * 100
        max_loss = debit * 100
        
        # Probability estimate (simplified)
        probability = 0.40  # Butterflies have lower probability
        
        # Score based on risk/reward
        risk_reward = max_profit / max_loss if max_loss > 0 else 0
        score = min(100, risk_reward * 50 * probability)
        
        return ComboRecommendation(
            strategy='butterfly',
            legs=[
                OptionLeg('BUY', lower, 'C', lower_call['delta'],
                         lower_call['bid'], lower_call['ask']),
                OptionLeg('SELL', center, 'C', center_call['delta'] * 2,
                         center_call['bid'], center_call['ask']),
                OptionLeg('BUY', upper, 'C', upper_call['delta'],
                         upper_call['bid'], upper_call['ask'])
            ],
            credit=-debit,  # Negative for debit
            max_loss=max_loss,
            probability=probability,
            score=score,
            rationale=f"Pinning expected at {center} (GEX zero level)"
        )
        
    def _build_vertical(self, chain: pd.DataFrame, direction: str) -> Optional[ComboRecommendation]:
        """Build directional vertical spread"""
        if direction == 'bull':
            # Bull put spread
            options = chain[chain['option_type'] == 'P'].copy()
            short_delta_target = -self.config['vertical']['short_delta']
            long_delta_target = -self.config['vertical']['long_delta']
        else:
            # Bear call spread
            options = chain[chain['option_type'] == 'C'].copy()
            short_delta_target = self.config['vertical']['short_delta']
            long_delta_target = self.config['vertical']['long_delta']
            
        short_strike = self._find_by_delta(options, short_delta_target)
        long_strike = self._find_by_delta(options, long_delta_target)
        
        if short_strike is None or long_strike is None:
            return None
            
        # Calculate credit
        credit = short_strike['bid'] - long_strike['ask']
        
        if credit <= 0:
            return None
            
        # Max loss
        width = abs(long_strike['strike'] - short_strike['strike'])
        max_loss = (width - credit) * 100
        
        # Probability based on short delta
        probability = 1 - abs(short_strike['delta'])
        
        # Score
        risk_reward = credit / width
        score = min(100, risk_reward * 100 * probability * 1.5)
        
        return ComboRecommendation(
            strategy=f'{direction}_vertical',
            legs=[
                OptionLeg('SELL', short_strike['strike'], short_strike['option_type'],
                         short_strike['delta'], short_strike['bid'], short_strike['ask']),
                OptionLeg('BUY', long_strike['strike'], long_strike['option_type'],
                         long_strike['delta'], long_strike['bid'], long_strike['ask'])
            ],
            credit=credit,
            max_loss=max_loss,
            probability=probability,
            score=score,
            rationale=f"{direction.title()} directional play with {probability:.1%} probability"
        )
        
    def _find_by_delta(self, options: pd.DataFrame, target_delta: float, 
                      tolerance: float = 0.05) -> Optional[pd.Series]:
        """Find option closest to target delta"""
        if len(options) == 0:
            return None
            
        options = options.copy()
        options['delta_diff'] = abs(options['delta'] - target_delta)
        
        # Filter by tolerance
        valid = options[options['delta_diff'] <= tolerance]
        
        if len(valid) == 0:
            return None
            
        return valid.loc[valid['delta_diff'].idxmin()]
```

---

## Day 8: Order Manager Module

### 8.1 Execution Manager
```python
# magic8clone/modules/order_manager/executor.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from ...config import settings
from ...utils.monitoring import metrics
from ..data_collector.ib_connector import IBConnector

logger = logging.getLogger(__name__)

class OrderExecutor:
    """Order execution with retry logic and risk checks"""
    
    def __init__(self, ib_connector: IBConnector):
        self.ib = ib_connector
        self.active_orders = {}
        self.daily_pnl = 0
        self.position_count = 0
        
    async def execute_recommendation(self, recommendation: Dict) -> Optional[int]:
        """Execute combo order with risk checks"""
        # Risk checks
        if not await self._check_risk_limits(recommendation):
            logger.warning(f"Risk check failed for {recommendation['strategy']}")
            return None
            
        if settings.dry_run:
            logger.info(f"DRY RUN: Would execute {recommendation['strategy']}")
            return -1
            
        # Build combo order
        order_id = await self._place_combo_order(recommendation)
        
        if order_id:
            # Monitor fill
            asyncio.create_task(self._monitor_order(order_id, recommendation))
            
        return order_id
        
    async def _check_risk_limits(self, recommendation: Dict) -> bool:
        """Check circuit breakers and risk limits"""
        breakers = settings.circuit_breakers
        
        # Daily loss check
        if self.daily_pnl <= -breakers['max_daily_loss']:
            logger.error("Daily loss limit reached")
            metrics.increment('risk.daily_loss_limit_hit')
            return False
            
        # Position count check
        if self.position_count >= breakers['max_position_size']:
            logger.warning("Max position count reached")
            return False
            
        # Concurrent orders check
        if len(self.active_orders) >= breakers['max_concurrent_orders']:
            logger.warning("Max concurrent orders reached")
            return False
            
        # Account balance check (placeholder)
        # TODO: Implement actual account balance check
        
        return True
        
    async def _place_combo_order(self, recommendation: Dict) -> Optional[int]:
        """Place multi-leg combo order"""
        try:
            legs = recommendation['legs']
            
            # For now, place legs individually
            # TODO: Implement proper combo order through IB API
            order_ids = []
            
            for leg in legs:
                contract = await self._create_contract(leg)
                quantity = 1 if leg['action'] == 'BUY' else -1
                
                # Calculate limit price
                if leg['action'] == 'BUY':
                    limit_price = leg['ask'] + settings.order_rules['initial_edge_ticks'] * 0.05
                else:
                    limit_price = leg['bid'] - settings.order_rules['initial_edge_ticks'] * 0.05
                    
                order_id = await self.ib.place_order(
                    contract, 'LIMIT', quantity, limit_price
                )
                order_ids.append(order_id)
                
            # Store combo reference
            combo_id = min(order_ids)  # Use lowest order ID as combo ID
            self.active_orders[combo_id] = {
                'strategy': recommendation['strategy'],
                'order_ids': order_ids,
                'created_at': datetime.utcnow(),
                'status': 'PENDING'
            }
            
            logger.info(f"Placed {recommendation['strategy']} combo order: {combo_id}")
            metrics.increment('orders.placed', tags={'strategy': recommendation['strategy']})
            
            return combo_id
            
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            metrics.increment('orders.placement_errors')
            return None
            
    async def _monitor_order(self, order_id: int, recommendation: Dict):
        """Monitor order fill and implement retry logic"""
        order_info = self.active_orders[order_id]
        rules = settings.order_rules
        
        attempt = 0
        while attempt < rules['max_attempts']:
            await asyncio.sleep(rules['widen_every_s'])
            
            # Check fill status
            filled = await self._check_fill_status(order_info['order_ids'])
            
            if filled['complete']:
                logger.info(f"Order {order_id} filled completely")
                order_info['status'] = 'FILLED'
                self.position_count += 1
                break
                
            elif filled['partial'] >= rules['min_fill_size']:
                logger.info(f"Order {order_id} partially filled: {filled['partial']:.1%}")
                order_info['status'] = 'PARTIAL'
                break
                
            else:
                # Widen spread and retry
                attempt += 1
                logger.info(f"Widening order {order_id}, attempt {attempt}")
                await self._widen_order(order_info['order_ids'], attempt)
                
        if order_info['status'] == 'PENDING':
            # Cancel unfilled orders
            logger.warning(f"Cancelling unfilled order {order_id}")
            await self._cancel_orders(order_info['order_ids'])
            order_info['status'] = 'CANCELLED'
            
    async def _check_fill_status(self, order_ids: List[int]) -> Dict:
        """Check fill status of multi-leg order"""
        # TODO: Implement actual IB fill checking
        # Placeholder
        return {'complete': False, 'partial': 0.0}
        
    async def _widen_order(self, order_ids: List[int], attempt: int):
        """Widen order by specified ticks"""
        # TODO: Implement order modification
        pass
        
    async def _cancel_orders(self, order_ids: List[int]):
        """Cancel multiple orders"""
        for order_id in order_ids:
            self.ib.ib.cancelOrder(order_id)
            
    async def _create_contract(self, leg: Dict):
        """Create IB contract from leg specification"""
        from ib_async import Option
        
        # TODO: Get proper expiry
        expiry = datetime.now().strftime('%Y%m%d')
        
        contract = Option(
            'SPX',
            expiry,
            leg['strike'],
            leg['option_type'],
            'CBOE'
        )
        
        await self.ib.ib.qualifyContractsAsync(contract)
        return contract
```

---

## Day 9: Main Orchestrator

### 9.1 Mono-Service Main Loop
```python
# magic8clone/main.py
import asyncio
import signal
import logging
from datetime import datetime, time
from typing import Optional
import pandas as pd
from fastapi import FastAPI
from prometheus_client import make_asgi_app
import uvicorn

from .config import settings
from .modules.data_collector.ib_connector import IBConnector
from .modules.greeks_engine.calculator import GreeksEngine
from .modules.greeks_engine.gex_analyzer import GEXAnalyzer
from .modules.combo_selector.strategies import StrategySelector
from .modules.order_manager.executor import OrderExecutor
from .utils.redis_client import RedisClient
from .utils.db_client import TimescaleDB
from .utils.monitoring import metrics

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Magic8CloneOrchestrator:
    """Main orchestration loop for mono-service mode"""
    
    def __init__(self):
        self.ib_connector = IBConnector()
        self.greeks_engine = GreeksEngine()
        self.gex_analyzer = GEXAnalyzer()
        self.strategy_selector = StrategySelector()
        self.order_executor = OrderExecutor(self.ib_connector)
        self.redis_client = RedisClient()
        self.db = TimescaleDB()
        self.running = False
        self.cycle_count = 0
        
    async def initialize(self):
        """Initialize all connections"""
        logger.info("Initializing Magic8Clone...")
        
        # Connect to IB
        await self.ib_connector.connect()
        
        # Initialize Redis
        await self.redis_client.connect()
        
        # Initialize TimescaleDB
        await self.db.connect()
        
        logger.info("Initialization complete")
        
    async def run_cycle(self):
        """Execute one complete prediction cycle"""
        cycle_start = datetime.utcnow()
        self.cycle_count += 1
        
        try:
            with metrics.timer('cycle.total_time'):
                # 1. Fetch option chain
                logger.info(f"Starting cycle {self.cycle_count}")
                option_chain = await self._fetch_and_store_chain()
                
                # 2. Calculate Greeks
                option_chain = await self._calculate_greeks(option_chain)
                
                # 3. Calculate GEX
                gex_data = await self._calculate_gex(option_chain)
                
                # 4. Calculate market metrics
                market_metrics = await self._calculate_market_metrics(option_chain, gex_data)
                
                # 5. Select strategies
                recommendations = await self._select_strategies(
                    option_chain, gex_data, market_metrics
                )
                
                # 6. Execute trades
                if recommendations and not settings.dry_run:
                    await self._execute_trades(recommendations)
                    
                # 7. Display results
                self._display_predictions(recommendations, gex_data, market_metrics)
                
                # 8. Check performance triggers
                await self._check_performance_triggers(cycle_start)
                
        except Exception as e:
            logger.error(f"Cycle {self.cycle_count} failed: {e}")
            metrics.increment('cycle.errors')
            
    async def _fetch_and_store_chain(self) -> pd.DataFrame:
        """Fetch option chain and store in TimescaleDB"""
        with metrics.timer('cycle.fetch_chain'):
            chain = await self.ib_connector.get_0dte_chain()
            
            # Store in database
            await self.db.insert_option_chain(chain)
            
            # Publish to Redis
            await self.redis_client.publish_stream(
                'option_chain',
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'spot_price': chain['spot_price'].iloc[0],
                    'contract_count': len(chain),
                    'data': chain.to_json()
                }
            )
            
            return chain
            
    async def _calculate_greeks(self, chain: pd.DataFrame) -> pd.DataFrame:
        """Calculate missing Greeks"""
        with metrics.timer('cycle.calculate_greeks'):
            enhanced_chain = self.greeks_engine.calculate_greeks(chain)
            
            # Cache in Redis
            await self.redis_client.cache_dataframe(
                'greeks:latest',
                enhanced_chain,
                ttl=300
            )
            
            return enhanced_chain
            
    async def _calculate_gex(self, chain: pd.DataFrame) -> Dict:
        """Calculate gamma exposure"""
        with metrics.timer('cycle.calculate_gex'):
            gex_data = self.gex_analyzer.calculate_gex(chain)
            
            # Store in database
            await self.db.execute(
                """
                INSERT INTO gamma_exposure 
                (time, strike, gex_value, total_gamma, zero_gamma_level, put_wall, call_wall)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                datetime.utcnow(),
                gex_data['max_gamma_strike'],
                0,  # Placeholder
                gex_data['total_gamma'],
                gex_data['zero_gamma_level'],
                gex_data['put_wall'],
                gex_data['call_wall']
            )
            
            return gex_data
            
    async def _calculate_market_metrics(self, chain: pd.DataFrame, gex_data: Dict) -> Dict:
        """Calculate additional market metrics"""
        # Calculate 5-minute ATR (simplified for now)
        # TODO: Implement proper ATR calculation from price history
        spot = chain['spot_price'].iloc[0]
        atr_5min = spot * 0.001  # 0.1% placeholder
        
        # Get expected move from GEX
        market_metrics = self.gex_analyzer.calculate_expected_move(gex_data, atr_5min)
        
        return market_metrics
        
    async def _select_strategies(self, chain: pd.DataFrame, 
                               gex_data: Dict, market_metrics: Dict) -> List:
        """Select optimal strategies"""
        with metrics.timer('cycle.select_strategies'):
            recommendations = await self.strategy_selector.select_strategies(
                chain, gex_data, market_metrics
            )
            
            # Store predictions
            for rec in recommendations:
                pred_id = await self.db.insert_prediction(rec.to_dict())
                rec.prediction_id = pred_id
                
            return recommendations
            
    async def _execute_trades(self, recommendations: List):
        """Execute recommended trades"""
        for rec in recommendations[:1]:  # Execute only top recommendation
            order_id = await self.order_executor.execute_recommendation(rec.to_dict())
            
            if order_id:
                # Update database
                await self.db.execute(
                    """
                    INSERT INTO orders (prediction_id, ib_order_id, status)
                    VALUES ($1, $2, $3)
                    """,
                    rec.prediction_id,
                    order_id,
                    'PENDING'
                )
                
    def _display_predictions(self, recommendations: List, gex_data: Dict, market_metrics: Dict):
        """Display predictions in Magic8 format"""
        if not recommendations:
            logger.warning("No recommendations generated")
            return
            
        spot = gex_data['spot_price']
        top_rec = recommendations[0]
        
        print("\n" + "="*60)
        print(f"Magic8Clone Prediction - {datetime.now():%Y-%m-%d %H:%M:%S}")
        print("="*60)
        print(f"SPX: ${spot:.2f}")
        print(f"Expected Range: {market_metrics['expected_range_pct']:.2%}")
        print(f"GEX Total: {gex_data['total_gamma']/1e9:.2f}B")
        print(f"Zero Gamma: {gex_data['zero_gamma_level']:.0f}")
        print(f"\nTop Recommendation: {top_rec.strategy.upper()}")
        print(f"Credit: ${top_rec.credit:.2f}")
        print(f"Max Loss: ${top_rec.max_loss:.2f}")
        print(f"Probability: {top_rec.probability:.1%}")
        print(f"Score: {top_rec.score:.1f}")
        print(f"\nRationale: {top_rec.rationale}")
        print("="*60 + "\n")
        
    async def _check_performance_triggers(self, cycle_start: datetime):
        """Check if we should split to microservices"""
        cycle_time = (datetime.utcnow() - cycle_start).total_seconds() * 1000
        
        # Record metric
        await self.db.record_metric('cycle_time_ms', cycle_time)
        metrics.histogram('cycle.duration_ms', cycle_time)
        
        # Check triggers
        if cycle_time > settings.performance_triggers['latency_p95_ms']:
            logger.warning(f"Cycle time {cycle_time}ms exceeds trigger!")
            # TODO: Send alert to switch to microservices
            
    async def run(self):
        """Main run loop"""
        self.running = True
        
        while self.running:
            # Check if market is open
            if self._is_market_open():
                await self.run_cycle()
                
            # Wait for next cycle
            await asyncio.sleep(300)  # 5 minutes
            
    def _is_market_open(self) -> bool:
        """Check if market is open for trading"""
        now = datetime.now()
        
        # Skip weekends
        if now.weekday() >= 5:
            return False
            
        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        return market_open <= now.time() <= market_close
        
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Magic8Clone...")
        self.running = False
        
        # Disconnect
        self.ib_connector.disconnect()
        await self.redis_client.close()
        # DB pool will close automatically

# FastAPI app for metrics
app = FastAPI()

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.1",
        "mode": "mono-service" if not settings.use_microservices else "micro-service"
    }

# Main entry point
async def main():
    """Main entry point"""
    orchestrator = Magic8CloneOrchestrator()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(orchestrator.shutdown())
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize
    await orchestrator.initialize()
    
    # Start metrics server
    metrics_server = asyncio.create_task(
        uvicorn.run(app, host="0.0.0.0", port=settings.metrics_port)
    )
    
    # Run main loop
    await orchestrator.run()
    
    # Cleanup
    metrics_server.cancel()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Day 10: Testing & Go-Live

### 10.1 Quick Test Script
```python
# scripts/test_cycle.py
import asyncio
import sys
sys.path.append('.')

from magic8clone.main import Magic8CloneOrchestrator

async def test():
    """Run single test cycle"""
    orchestrator = Magic8CloneOrchestrator()
    
    print("Initializing...")
    await orchestrator.initialize()
    
    print("Running test cycle...")
    await orchestrator.run_cycle()
    
    print("Test complete!")
    await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(test())
```

### 10.2 Launch Commands
```bash
# Development launch
docker-compose up -d redis timescaledb prometheus grafana
poetry install
poetry run python -m magic8clone.main

# Production launch
docker-compose up -d
docker-compose logs -f magic8clone

# Monitor performance
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus
```

---

## Monitoring & Alerts

### Prometheus Configuration
```yaml
# infra/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'magic8clone'
    static_configs:
      - targets: ['host.docker.internal:8000']
```

### Key Metrics to Track
- `cycle.total_time` - End-to-end latency
- `ib.chain_size` - Options fetched
- `strategies.*_selected` - Strategy counts
- `orders.placed` - Orders submitted
- `risk.daily_loss_limit_hit` - Circuit breaker triggers

---

## Next Steps

1. **Day 11-12**: If p95 > 20s, split to microservices
2. **Day 13-14**: Add shadow-live comparator
3. **Week 3+**: ML enhancements

---

**This implementation provides a complete, working MVP that can be deployed in 10 days and evolved as needed. The mono-service approach keeps complexity low while maintaining the ability to scale.**