#!/usr/bin/env python3
"""
Test script for IBKR market data integration.
Tests real market data fetching with Greeks from Interactive Brokers.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from magic8_companion.modules.ibkr_market_data import IBKRMarketData, IBKRConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def check_market_hours():
    """Check if market is open."""
    now = datetime.now()
    
    # Check if it's a weekday
    if now.weekday() > 4:  # Saturday = 5, Sunday = 6
        return False, "Market closed - Weekend"
    
    # Market hours in ET (9:30 AM - 4:00 PM)
    # This is simplified - you'd want to handle holidays and time zones properly
    hour = now.hour
    minute = now.minute
    
    if hour < 9 or (hour == 9 and minute < 30):
        return False, "Market closed - Before 9:30 AM ET"
    elif hour >= 16:
        return False, "Market closed - After 4:00 PM ET"
    else:
        return True, "Market open"


async def test_ibkr_connection():
    """Test basic IBKR connection."""
    print("\n" + "="*60)
    print("Testing IBKR Connection")
    print("="*60)
    
    ibkr = IBKRMarketData()
    
    try:
        connected = await ibkr.connect()
        if connected:
            print("✅ Successfully connected to IBKR TWS/Gateway")
            print(f"   Host: {ibkr.host}")
            print(f"   Port: {ibkr.port}")
            print(f"   Client ID: {ibkr.client_id}")
            await ibkr.disconnect()
            return True
        else:
            print("❌ Failed to connect to IBKR")
            print("   Please ensure TWS or IB Gateway is running")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def test_symbol_data(symbol: str):
    """Test fetching market data for a symbol."""
    print(f"\n{'='*60}")
    print(f"Testing {symbol} Market Data")
    print(f"{'='*60}")
    
    ibkr = IBKRMarketData()
    
    async with IBKRConnection(ibkr) as market_data:
        try:
            # Fetch market data
            print(f"Fetching data for {symbol}...")
            data = await market_data.get_market_data(symbol)
            
            if data:
                print(f"\n✅ Successfully fetched data for {symbol}")
                print(f"\nMarket Overview:")
                print(f"  Symbol: {data['symbol']}")
                print(f"  Spot Price: ${data['spot_price']:.2f}")
                print(f"  IV Percentile: {data['iv_percentile']:.1f}%")
                print(f"  Expected Range: ±{data['expected_range_pct']:.2%}")
                print(f"  Gamma Environment: {data['gamma_environment']}")
                print(f"  Data Source: {data['data_source']}")
                print(f"  Timestamp: {data['analysis_timestamp']}")
                
                # Show option chain details
                option_chain = data['option_chain']
                if option_chain:
                    print(f"\nOption Chain Details:")
                    print(f"  Strikes: {len(option_chain)}")
                    print(f"  Time to Expiry: {option_chain[0]['time_to_expiry']:.4f} years")
                    
                    # Find ATM option
                    spot = data['spot_price']
                    atm = min(option_chain, key=lambda x: abs(x['strike'] - spot))
                    
                    print(f"\nATM Option (Strike: ${atm['strike']}):")
                    print(f"  Implied Vol: {atm['implied_volatility']*100:.1f}%")
                    print(f"  Call Greeks:")
                    print(f"    Delta: {atm['call_delta']:.4f}")
                    print(f"    Gamma: {atm['call_gamma']:.6f}")
                    print(f"    Theta: {atm['call_theta']:.4f}")
                    print(f"    Vega: {atm['call_vega']:.4f}")
                    print(f"  Put Greeks:")
                    print(f"    Delta: {atm['put_delta']:.4f}")
                    print(f"    Gamma: {atm['put_gamma']:.6f}")
                    print(f"    Theta: {atm['put_theta']:.4f}")
                    print(f"    Vega: {atm['put_vega']:.4f}")
                    print(f"  Volume: Call={atm['call_volume']}, Put={atm['put_volume']}")
                    print(f"  OI: Call={atm['call_open_interest']}, Put={atm['put_open_interest']}")
                    
                    # Show strikes summary
                    print(f"\nStrikes Summary:")
                    print(f"  Range: ${min(opt['strike'] for opt in option_chain):.2f} - "
                          f"${max(opt['strike'] for opt in option_chain):.2f}")
                    
                    # Sample 3 strikes
                    print(f"\n  Sample Strikes:")
                    sample_indices = [0, len(option_chain)//2, -1]
                    for idx in sample_indices:
                        opt = option_chain[idx]
                        print(f"    ${opt['strike']}: "
                              f"IV={opt['implied_volatility']*100:.1f}%, "
                              f"C_Gamma={opt['call_gamma']:.6f}, "
                              f"P_Gamma={opt['put_gamma']:.6f}")
                
                return True
            else:
                print(f"❌ Failed to fetch data for {symbol}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing {symbol}: {e}")
            logger.exception("Detailed error:")
            return False


async def compare_with_yahoo(symbol: str):
    """Compare IBKR data with Yahoo Finance data."""
    print(f"\n{'='*60}")
    print(f"Comparing IBKR vs Yahoo Finance for {symbol}")
    print(f"{'='*60}")
    
    # Fetch from IBKR
    ibkr = IBKRMarketData()
    ibkr_data = None
    
    async with IBKRConnection(ibkr) as market_data:
        ibkr_data = await market_data.get_market_data(symbol)
    
    # Fetch from Yahoo
    from magic8_companion.modules.real_market_data import RealMarketData
    yahoo = RealMarketData()
    yahoo_data = await yahoo.get_market_data(symbol)
    
    if ibkr_data and yahoo_data:
        print(f"\nData Comparison:")
        print(f"{'Metric':<20} {'IBKR':>15} {'Yahoo':>15} {'Difference':>15}")
        print("-" * 65)
        
        # Compare prices
        ibkr_price = ibkr_data['spot_price']
        yahoo_price = yahoo_data['spot_price']
        price_diff = abs(ibkr_price - yahoo_price)
        print(f"{'Spot Price':<20} ${ibkr_price:>14.2f} ${yahoo_price:>14.2f} ${price_diff:>14.2f}")
        
        # Compare IV
        ibkr_iv = ibkr_data['iv_percentile']
        yahoo_iv = yahoo_data['iv_percentile']
        iv_diff = abs(ibkr_iv - yahoo_iv)
        print(f"{'IV Percentile':<20} {ibkr_iv:>14.1f}% {yahoo_iv:>14.1f}% {iv_diff:>14.1f}%")
        
        # Compare expected range
        ibkr_range = ibkr_data['expected_range_pct']
        yahoo_range = yahoo_data['expected_range_pct']
        range_diff = abs(ibkr_range - yahoo_range)
        print(f"{'Expected Range':<20} {ibkr_range*100:>14.2f}% {yahoo_range*100:>14.2f}% {range_diff*100:>14.2f}%")
        
        # Compare option chain sizes
        ibkr_strikes = len(ibkr_data['option_chain'])
        yahoo_strikes = len(yahoo_data['option_chain'])
        print(f"{'Option Strikes':<20} {ibkr_strikes:>15} {yahoo_strikes:>15} {abs(ibkr_strikes-yahoo_strikes):>15}")
        
        # Compare gamma environment
        print(f"{'Gamma Environment':<20}")
        print(f"  IBKR:  {ibkr_data['gamma_environment']}")
        print(f"  Yahoo: {yahoo_data['gamma_environment']}")
        
        # Key advantages of IBKR
        print(f"\n✅ IBKR Advantages:")
        print(f"  - Real-time data (Yahoo is 15-min delayed)")
        print(f"  - Accurate Greeks from exchange")
        print(f"  - Better bid/ask spreads")
        print(f"  - More reliable during high volume")
        
    else:
        if not ibkr_data:
            print("❌ Failed to fetch IBKR data")
        if not yahoo_data:
            print("❌ Failed to fetch Yahoo data")


async def main():
    """Main test function."""
    print("\n" + "="*60)
    print("IBKR Market Data Integration Test")
    print("="*60)
    
    # Check environment
    print("\nEnvironment Configuration:")
    print(f"  USE_IBKR_DATA: {os.getenv('USE_IBKR_DATA', 'false')}")
    print(f"  IBKR_HOST: {os.getenv('IBKR_HOST', '127.0.0.1')}")
    print(f"  IBKR_PORT: {os.getenv('IBKR_PORT', '7497')}")
    print(f"  IBKR_CLIENT_ID: {os.getenv('IBKR_CLIENT_ID', '1')}")
    print(f"  IBKR_FALLBACK_TO_YAHOO: {os.getenv('IBKR_FALLBACK_TO_YAHOO', 'true')}")
    
    # Check market hours
    is_open, status = await check_market_hours()
    print(f"\nMarket Status: {status}")
    if not is_open:
        print("⚠️  Note: Options data may be stale outside market hours")
    
    # Test connection
    if not await test_ibkr_connection():
        print("\n❌ Cannot proceed without IBKR connection")
        print("\nTroubleshooting:")
        print("1. Ensure TWS or IB Gateway is running")
        print("2. Check API settings are enabled in TWS")
        print("3. Verify port number (7497 for paper, 7496 for live)")
        print("4. Check firewall settings")
        return
    
    # Get symbols to test
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM']
    
    print(f"\nTesting symbols: {', '.join(symbols)}")
    
    # Test each symbol
    success_count = 0
    for symbol in symbols:
        if await test_symbol_data(symbol):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Test Summary: {success_count}/{len(symbols)} symbols successful")
    print(f"{'='*60}")
    
    # Optional: Compare with Yahoo (only for first symbol)
    if success_count > 0 and '--compare' in sys.argv:
        await compare_with_yahoo(symbols[0])


if __name__ == "__main__":
    # Check for help
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
IBKR Market Data Test Script

Usage:
    python test_ibkr_market_data.py [symbols...] [options]

Examples:
    python test_ibkr_market_data.py                    # Test SPY, QQQ, IWM
    python test_ibkr_market_data.py AAPL MSFT TSLA    # Test specific symbols
    python test_ibkr_market_data.py SPY --compare     # Compare with Yahoo

Options:
    --compare    Compare IBKR data with Yahoo Finance
    --help, -h   Show this help message

Environment Variables:
    IBKR_HOST              TWS/Gateway host (default: 127.0.0.1)
    IBKR_PORT              TWS/Gateway port (default: 7497)
    IBKR_CLIENT_ID         Client ID (default: 1)
    IBKR_FALLBACK_TO_YAHOO Use Yahoo if IBKR fails (default: true)
""")
        sys.exit(0)
    
    # Run async main
    asyncio.run(main())
