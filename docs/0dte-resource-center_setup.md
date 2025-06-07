# 0DTE Option Combo Prediction System - Complete Resource Center

## 🚀 Quick Setup (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/0dte-system/main/setup.sh | bash
```

## 📁 Project Structure

```
0dte-trading-system/
├── core/
│   ├── gamma-exposure/      # Gamma exposure calculators
│   ├── ib-integration/      # Interactive Brokers connections
│   ├── greeks-engine/       # Options calculations
│   └── ml-models/           # Machine learning components
├── strategies/
│   ├── 0dte-systems/        # 0DTE specific implementations
│   └── backtesting/         # Strategy testing frameworks
├── data/
│   ├── real-time/           # Live data feeds
│   └── historical/          # Backtesting data
├── visualization/           # Strategy visualization tools
├── platforms/              # Complete trading platforms
└── scripts/                # Setup and utility scripts
```

## 🛠️ Master Setup Script

Save this as `setup_0dte_system.sh`:

```bash
#!/bin/bash

# 0DTE Trading System Complete Setup Script
# This script clones all repositories and installs dependencies

echo "🚀 Setting up 0DTE Option Combo Prediction System..."

# Create main directory structure
mkdir -p 0dte-trading-system/{core,strategies,data,visualization,platforms,scripts}
cd 0dte-trading-system

# Core Components
echo "📦 Cloning Core Components..."

# Gamma Exposure Analysis
mkdir -p core/gamma-exposure
cd core/gamma-exposure
git clone https://github.com/jensolson/SPX-Gamma-Exposure.git
git clone https://github.com/Matteo-Ferrara/gex-tracker.git
git clone https://github.com/phammings/SPX500-Gamma-Exposure-Calculator.git
cd ../..

# Interactive Brokers Integration
mkdir -p core/ib-integration
cd core/ib-integration
git clone https://github.com/ib-api-reloaded/ib_async.git
git clone https://github.com/erdewit/ib_insync.git  # Legacy reference
cd ../..

# Greeks Calculation Engine
mkdir -p core/greeks-engine
cd core/greeks-engine
git clone https://github.com/vollib/py_vollib.git
git clone https://github.com/marcdemers/py_vollib_vectorized.git
cd ../..

# Machine Learning Models
mkdir -p core/ml-models
cd core/ml-models
git clone https://github.com/mmfill/iron-condor.git
git clone https://github.com/nataliaburrey/Options_Trading_ML.git
cd ../..

# Strategy Components
echo "📊 Cloning Strategy Components..."

# 0DTE Specific Systems
mkdir -p strategies/0dte-systems
cd strategies/0dte-systems
git clone https://github.com/aicheung/0dte-trader.git
git clone https://github.com/webclinic017/ToS-with-Python-0DTE-.git
cd ../..

# Backtesting Frameworks
mkdir -p strategies/backtesting
cd strategies/backtesting
git clone https://github.com/foxbupt/optopsy.git
cd ../..

# Data Sources
echo "📡 Cloning Data Source Integrations..."

# Alternative Data Sources
mkdir -p data/real-time
cd data/real-time
git clone https://github.com/jessecooper/pyetrade.git
git clone https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer.git
git clone https://github.com/mcdallas/wallstreet.git
cd ../..

# Visualization Tools
echo "📈 Cloning Visualization Tools..."
cd visualization
git clone https://github.com/hashABCD/opstrat.git
cd ..

# Complete Trading Platforms
echo "🏗️ Cloning Complete Trading Platforms..."
cd platforms
git clone https://github.com/QuantConnect/Lean.git
git clone https://github.com/nautechsystems/nautilus_trader.git
cd ..

echo "✅ All repositories cloned successfully!"
```

## 📋 Repository Catalog

### 🎯 Core Components

#### Gamma Exposure Analysis

**1. jensolson/SPX-Gamma-Exposure** ⭐ 124 | 🍴 48
```bash
git clone https://github.com/jensolson/SPX-Gamma-Exposure.git
```
- **Features**: CBOE data integration, Black-Scholes Greeks, sensitivity analysis
- **Key Functions**: `CBOE_GEX()`, `CBOE_Greeks()`
- **Language**: Python
- **Last Updated**: Active

**2. Matteo-Ferrara/gex-tracker** ⭐ 118 | 🍴 42  
```bash
git clone https://github.com/Matteo-Ferrara/gex-tracker.git
```
- **Features**: Real-time CBOE scraping, interactive visualizations
- **Supports**: SPX, SPY, multiple tickers
- **Language**: Python
- **Special**: Beautiful custom chart styling

**3. OptionGreeksGPU** (PyPI Package)
```bash
pip install OptionGreeksGPU
```
- **Performance**: 1,500x faster than pure Python
- **Benchmark**: 1,648 contracts in 0.14 seconds
- **Language**: Python with GPU acceleration

#### Interactive Brokers Integration

**4. ib-api-reloaded/ib_async** (Recommended)
```bash
git clone https://github.com/ib-api-reloaded/ib_async.git
pip install ib_async
```
- **Features**: Asyncio-based, production-ready error handling
- **Support**: Real-time streaming, auto-reconnection
- **Note**: Maintained successor to ib_insync

#### High-Performance Options Libraries

**5. marcdemers/py_vollib_vectorized**
```bash
git clone https://github.com/marcdemers/py_vollib_vectorized.git
pip install py-vollib-vectorized
```
- **Performance**: 2.4x faster than py_vollib
- **Features**: Vectorized Greeks, DataFrame integration
- **Best For**: Processing thousands of contracts

### 🎲 0DTE Trading Systems

**6. aicheung/0dte-trader** (Most Complete)
```bash
git clone https://github.com/aicheung/0dte-trader.git
```
- **Strategies**: Iron Condor, Iron Butterfly, Bull/Bear spreads, Butterfly
- **Features**: Automated order management, profit-taking, stop-loss
- **API**: Interactive Brokers

**7. foxbupt/optopsy** ⭐ 600+
```bash
git clone https://github.com/foxbupt/optopsy.git
pip install optopsy
```
- **Features**: Comprehensive backtesting, strategy optimization
- **Supports**: All major option strategies
- **Special**: Modular filter-based construction

### 📊 Visualization & Analysis

**8. hashABCD/opstrat**
```bash
git clone https://github.com/hashABCD/opstrat.git
pip install opstrat
```
- **Features**: Payoff diagrams, Yahoo Finance integration
- **Supports**: Complex multi-leg strategies

### 🤖 Machine Learning Components

**9. mmfill/iron-condor**
```bash
git clone https://github.com/mmfill/iron-condor.git
```
- **Models**: Feedforward NN, LSTM
- **Purpose**: Optimal strike price prediction
- **Approach**: Stationary time series analysis

### 🏗️ Complete Platforms

**10. QuantConnect/Lean** ⭐ 37,000+
```bash
git clone https://github.com/QuantConnect/Lean.git
```
- **Language**: C#/.NET with Python support
- **Features**: Event-driven backtesting, live trading
- **Scale**: Professional-grade platform

## 📦 Python Dependencies Installation

### Essential Packages
```bash
# Core dependencies
pip install numpy pandas matplotlib seaborn jupyter

# Interactive Brokers
pip install ib_async

# Options calculations
pip install py-vollib-vectorized
pip install QuantLib-Python

# Data sources
pip install yfinance pyetrade
pip install beautifulsoup4 requests

# Machine Learning
pip install scikit-learn tensorflow torch
pip install statsmodels prophet

# Visualization
pip install opstrat plotly dash

# Performance
pip install numba joblib ray
pip install OptionGreeksGPU  # If GPU available

# Additional utilities
pip install asyncio aiohttp websockets
pip install redis celery
pip install sqlalchemy psycopg2
```

### Create Requirements File
```bash
# Save all dependencies
pip freeze > requirements.txt
```

## 🐳 Docker Setup (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

CMD ["python", "main.py"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  0dte-system:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - IB_GATEWAY_HOST=ib-gateway
      - REDIS_HOST=redis
    depends_on:
      - redis
      - ib-gateway

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  ib-gateway:
    image: ghcr.io/extrange/ibkr:latest
    ports:
      - "4001:4001"
      - "4002:4002"
    environment:
      - TWS_USERID=${TWS_USERID}
      - TWS_PASSWORD=${TWS_PASSWORD}
```

## 🚦 Getting Started Guide

### Step 1: Initial Setup
```bash
# Run the master setup script
chmod +x setup_0dte_system.sh
./setup_0dte_system.sh

# Navigate to project
cd 0dte-trading-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 2: Configure Interactive Brokers
```python
# config/ib_config.py
IB_CONFIG = {
    'host': '127.0.0.1',
    'port': 7497,  # TWS Paper Trading
    'clientId': 1,
    'account': 'YOUR_ACCOUNT_ID'
}
```

### Step 3: Test Core Components
```python
# test_setup.py
import asyncio
from ib_async import IB
import py_vollib_vectorized as vol
import numpy as np

async def test_ib_connection():
    ib = IB()
    await ib.connectAsync('127.0.0.1', 7497, clientId=1)
    print(f"Connected: {ib.isConnected()}")
    await ib.disconnect()

# Test Greeks calculation
S = 100  # Underlying price
K = np.array([90, 95, 100, 105, 110])  # Strikes
T = 1/365  # 1 day to expiration
r = 0.05  # Risk-free rate
sigma = 0.2  # Volatility

# Calculate all Greeks at once
calls = vol.black_scholes.greeks.analytical.delta('c', S, K, T, r, sigma)
print(f"Call Deltas: {calls}")

asyncio.run(test_ib_connection())
```

### Step 4: Run Example 0DTE Strategy
```python
# example_strategy.py
from core.gamma_exposure.SPX_Gamma_Exposure.GEX import CBOE_GEX
from strategies.formation_predictor import FormationPredictor

# Calculate current gamma exposure
gex_data = CBOE_GEX()
print(f"Current GEX: {gex_data['total_gamma']}")

# Predict optimal formation
predictor = FormationPredictor()
recommendation = predictor.predict(
    spot_price=5850,
    gamma_exposure=gex_data,
    time_to_expiry=0.25  # 0DTE
)

print(f"Recommended Formation: {recommendation}")
```

## 🏗️ Architecture Blueprint

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                     │
├─────────────────┬───────────────────┬───────────────────────┤
│  IB Real-Time   │   CBOE Options    │   Alternative APIs    │
│   (ib_async)    │  (gex-tracker)    │    (pyetrade)        │
└────────┬────────┴─────────┬─────────┴───────────┬───────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Processing Engine                         │
├─────────────────┬───────────────────┬───────────────────────┤
│ Greeks Calculator│ Gamma Analysis    │   ML Predictions      │
│ (py_vollib_vec) │ (SPX-GEX)         │  (iron-condor)       │
└────────┬────────┴─────────┬─────────┴───────────┬───────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Strategy Formation Layer                    │
├─────────────────────────────────────────────────────────────┤
│           0DTE Combo Predictor (Magic8 Clone)               │
│   • Iron Condor • Butterfly • Vertical Spread               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
├─────────────────────────────────────────────────────────────┤
│     Order Management │ Risk Control │ Position Tracking      │
└─────────────────────────────────────────────────────────────┘
```

### Integration Pattern
```python
# main_system.py
class Magic8Clone:
    def __init__(self):
        self.ib = IBConnection()
        self.gamma_analyzer = GammaExposureAnalyzer()
        self.greeks_engine = GreeksEngine()
        self.ml_predictor = MLPredictor()
        self.strategy_former = StrategyFormation()
        
    async def run_prediction_cycle(self):
        # 1. Fetch live option chain
        option_chain = await self.ib.get_spx_options()
        
        # 2. Calculate Greeks
        greeks = self.greeks_engine.calculate_all(option_chain)
        
        # 3. Analyze gamma exposure
        gamma_exposure = self.gamma_analyzer.calculate_gex(option_chain)
        
        # 4. Generate predictions
        predictions = self.ml_predictor.predict(
            greeks=greeks,
            gamma=gamma_exposure,
            volume=option_chain.volume,
            open_interest=option_chain.open_interest
        )
        
        # 5. Form option combos
        recommendations = self.strategy_former.create_combos(predictions)
        
        return recommendations
```

## 📚 Additional Resources

### Documentation Links
- [Interactive Brokers API Guide](https://interactivebrokers.github.io/tws-api/)
- [py_vollib Documentation](https://py-vollib.readthedocs.io/)
- [QuantLib Python Cookbook](https://quantlib-python-cookbook.readthedocs.io/)

### Community Resources
- [/r/thetagang](https://reddit.com/r/thetagang) - Options selling strategies
- [Elite Trader Forums](https://www.elitetrader.com/et/) - Algorithmic trading discussions
- [QuantConnect Community](https://www.quantconnect.com/forum) - Strategy development

### Research Papers
- "The Gamma Exposure of S&P 500 Options" - Academic foundation
- "0DTE Options: Characteristics and Trading Strategies" - Strategy analysis
- "Machine Learning for Options Trading" - ML applications

## 🔧 Troubleshooting

### Common Issues

**IB Connection Failed**
```bash
# Check TWS/Gateway is running
# Ensure API connections are enabled in TWS
# Verify port settings (7497 for TWS, 4001 for Gateway)
```

**Module Import Errors**
```bash
# Ensure virtual environment is activated
# Reinstall problem package
pip install --force-reinstall package_name
```

**GPU Acceleration Not Working**
```bash
# Check CUDA installation
nvidia-smi
# Install CUDA toolkit if needed
```

## 📄 License & Disclaimer

This resource center is for educational purposes. Always test strategies thoroughly before live trading. Options trading involves substantial risk of loss.

---

**Created for the 0DTE Option Combo Prediction System Project**
*Last Updated: June 2025*