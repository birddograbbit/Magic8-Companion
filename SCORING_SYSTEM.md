# Magic8 Scoring System Documentation

## Overview
The Magic8 scoring system evaluates three trading strategies (Butterfly, Iron Condor, Vertical) based on market conditions and assigns scores from 0-100. Only strategies with HIGH confidence (score ≥ 75) will be executed by DiscordTrading.

## Scoring Components

### 1. Butterfly Strategy
Butterflies are preferred in low volatility, tight range environments with potential pinning.

**Scoring Criteria:**
- **IV Percentile**
  - < 40%: +30 points (ideal low volatility)
  - 40-60%: +15 points (acceptable volatility)
  - > 60%: 0 points (too volatile)

- **Expected Range**
  - < 0.6%: +35 points (very tight range)
  - 0.6-1.0%: +20 points (acceptable range)
  - > 1.0%: 0 points (too wide)

- **Gamma Environment Bonuses**
  - "high gamma" or "pinning": +20 points
  - "low volatility": +15 points

**Maximum Score: 100 points**

### 2. Iron Condor Strategy
Iron Condors (Sonar in Discord) work best in moderate volatility, range-bound markets.

**Scoring Criteria:**
- **IV Percentile**
  - 30-80%: +25 points (moderate volatility range)
  - > 40%: +20 points (credit spread benefit)

- **Expected Range**
  - < 1.2%: +30 points (range-bound)
  - 1.2-1.5%: +15 points (slightly wider)
  - > 1.5%: 0 points

- **Gamma Environment Bonuses**
  - "range-bound" or "moderate": +15 points

**Maximum Score: 90 points**

### 3. Vertical Strategy
Verticals excel in higher volatility with directional movement expectations.

**Scoring Criteria:**
- **IV Percentile**
  - > 50%: +25 points (high IV for credit spreads)
  - 40-50%: +10 points
  - < 40%: 0 points

- **Expected Range**
  - > 1.0%: +30 points (directional movement)
  - 0.8-1.0%: +15 points
  - < 0.8%: 0 points

- **Gamma Environment Bonuses**
  - "directional" or "variable": +25 points
  - "high volatility": +20 points

**Maximum Score: 100 points**

## Confidence Levels
- **HIGH**: Score ≥ 75 (will execute trade)
- **MEDIUM**: Score 50-74 (will skip)
- **LOW**: Score < 50 (will skip)

## Market Data Inputs
The scoring system uses three main inputs:
1. **IV Percentile**: Implied volatility rank (0-100)
2. **Expected Range %**: Projected price movement as percentage
3. **Gamma Environment**: Descriptive market conditions

## Example Scenarios

### Scenario 1: Low Volatility Pinning
- IV: 25%, Range: 0.4%, Environment: "Low volatility, high gamma"
- Butterfly: 30 + 35 + 20 + 15 = **100 (HIGH)**
- Iron Condor: 0 + 30 + 0 = **30 (LOW)**
- Vertical: 0 + 0 + 0 = **0 (LOW)**

### Scenario 2: Moderate Range-Bound
- IV: 45%, Range: 0.8%, Environment: "Range-bound, moderate gamma"
- Butterfly: 15 + 20 + 0 = **35 (LOW)**
- Iron Condor: 25 + 30 + 15 + 20 = **90 (HIGH)**
- Vertical: 10 + 15 + 0 = **25 (LOW)**

### Scenario 3: High Volatility Directional
- IV: 75%, Range: 1.5%, Environment: "High volatility, directional"
- Butterfly: 0 + 0 + 0 = **0 (LOW)**
- Iron Condor: 25 + 0 + 0 + 20 = **45 (LOW)**
- Vertical: 25 + 30 + 25 + 20 = **100 (HIGH)**

## Mock Data Generation
The system generates realistic market scenarios including:
- Low volatility scenarios (IV 25-35%)
- Moderate volatility (IV 45-55%)
- High volatility (IV 65-85%)

Each symbol has adjustments:
- SPX: -10% volatility (more stable)
- QQQ: +10% volatility (tech sector)
- RUT: +20% volatility (small caps)

Random noise of ±10% is added for variation.

## Important Notes
1. Only strategies scoring ≥75 will trigger trades
2. The system outputs ALL strategies' scores, not just the best one
3. DiscordTrading checks specific strategy confidence, not overall recommendation
4. Mock data changes every minute to simulate market movement
