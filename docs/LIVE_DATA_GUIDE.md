# Live Data Configuration Guide

This guide explains how to configure Magic8-Companion for live market data, with a focus on Interactive Brokers integration.

## Data Provider Priority

The system now prioritizes data sources as follows:
1. **Interactive Brokers (IB)** - Primary source for real-time options data
2. **Yahoo Finance** - Fallback for when IB is unavailable
3. **Mock Data** - Testing and development

## Interactive Brokers Setup

### Prerequisites
1. Active IB account with live options data subscription
2. IB Gateway or Trader Workstation (TWS) running
3. API connections enabled in IB Gateway/TWS

### Configuration Steps

1. **Enable API in IB Gateway/TWS:**
   - Go to Configure → Settings → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Add trusted IP: 127.0.0.1
   - Set Socket port (default: 7497 for live, 7496 for paper)

2. **Configure Magic8-Companion:**
   ```bash
   # In your .env file:
   M8C_USE_MOCK_DATA=false
   M8C_MARKET_DATA_PROVIDER=ib
   M8C_IB_HOST=127.0.0.1
   M8C_IB_PORT=7497        # 7496 for paper trading
   M8C_IB_CLIENT_ID=2      # Unique ID for this connection
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Data Flow

When requesting market data:
1. System attempts IB connection first
2. Fetches ATM options with Greeks and IV
3. Calculates IV percentile from historical data
4. Falls back to Yahoo if IB fails
5. Returns mock data if all else fails

## IV Percentile Calculation

The system now properly calculates IV percentile:
- Stores rolling 252-day history of IV values
- Calculates current IV's percentile rank
- Uses heuristics until sufficient history builds up

## Strategy Selection Thresholds (Research-Based)

### Butterfly Strategy
- **Optimal:** IV Percentile < 20%
- **Good:** IV Percentile < 30%
- **Range:** Daily expected move < 0.6%
- **Best for:** Low volatility, gamma pinning environments

### Iron Condor (Sonar)
- **Optimal:** IV Percentile 40-60%
- **Good:** IV Percentile 30-70%
- **Range:** Daily expected move < 1.0%
- **Best for:** Range-bound markets with moderate volatility

### Vertical Spreads
- **Optimal:** IV Percentile > 70%
- **Good:** IV Percentile > 50%
- **Range:** Daily expected move > 1.0%
- **Best for:** Directional markets with high volatility

## Testing Live Data

1. **Test IB Connection:**
   ```bash
   python -m magic8_companion.modules.ib_client
   ```

2. **Test Full System:**
   ```bash
   python test_live_data.py
   ```

3. **Run Production:**
   ```bash
   python -m magic8_companion.main
   ```

## Troubleshooting

### IB Connection Issues
- Verify IB Gateway/TWS is running
- Check API settings are enabled
- Ensure correct port (7497 live, 7496 paper)
- Check firewall isn't blocking connection
- Verify market data subscriptions are active

### IV Data Issues
- IB provides IV through modelGreeks
- Requires options data subscription
- May return None outside market hours
- System will build IV history over time

### Fallback Behavior
- If IB fails, Yahoo Finance is used automatically
- Yahoo has 15-20 minute delay
- Less accurate IV calculations
- Still suitable for testing

## Performance Considerations

- IB connection adds ~1-2 seconds per symbol
- First connection may take longer
- Maintain persistent connection for production
- IV history improves accuracy over time
