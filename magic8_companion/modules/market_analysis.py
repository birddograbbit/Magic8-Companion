from typing import Dict, List, Any, Optional
import numpy as np
from ..modules.ib_client import IBClient # Ensure this path is correct
import json # Added for GEX file reading
import datetime # Added for GEX file reading
from pathlib import Path # Added for GEX file reading
# Option 1: Try to use the existing GEX analysis if it can be adapted or if we simplify its input requirements.
# from .. import gex_analysis # This is magic8_companion/gex_analysis.py
# For now, let's assume gex_analysis.py might be too complex to integrate directly without modification.
# So, gex_flip will be a placeholder or derived differently for MVP.

def calculate_simple_iv_rank(current_avg_iv: float) -> int:
    """
    Calculates a simplified IV rank based on predefined thresholds.
    This is a placeholder for a proper IV rank calculation against historical data.
    Example thresholds (adjust based on SPX typical IV ranges):
    Low: < 0.15 (e.g., VIX < 15)
    Medium: 0.15 - 0.25
    High: > 0.25
    Returns a percentile-like score: 0-33 (Low), 34-66 (Medium), 67-100 (High)
    """
    if current_avg_iv < 0.15: # Example threshold for "low"
        return 25 # Represents low IV (e.g., 0-33rd percentile)
    elif current_avg_iv <= 0.25: # Example threshold for "medium"
        return 50 # Represents medium IV (e.g., 34-66th percentile)
    else:
        return 75 # Represents high IV (e.g., 67-100th percentile)

async def get_market_analysis(ib_client: IBClient, magic8_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Lightweight market analysis for combo scoring using data from IBClient.
    magic8_data can be optionally passed to use some of its values as placeholders if needed.
    """
    atm_options: List[Dict] = []
    avg_iv = 0.15 # Default IV if fetch fails
    avg_spread = 2.0 # Default spread if fetch fails
    iv_rank = 50 # Default IV rank
    gex_flip = 0 # Default GEX flip

    # --- GEX Flip Logic: Read from file, then fallback ---
    # Path assumes market_analysis.py is in magic8_companion/modules/
    # and data directory is at the project root.
    gex_file_path = Path(__file__).resolve().parent.parent.parent / "data" / "gex_data.json"
    gex_data_max_age_hours = 2 # Consider data stale after 2 hours

    gex_flip_from_file = None
    try:
        if gex_file_path.exists():
            with open(gex_file_path, 'r') as f:
                gex_data_file_content = json.load(f)

            timestamp_str = gex_data_file_content.get("last_calculated_timestamp")
            if timestamp_str:
                last_calc_time = datetime.datetime.fromisoformat(timestamp_str)
                # Ensure timezone awareness if comparing (GEX.py saves UTC)
                if last_calc_time.tzinfo is None: # If saved as naive, assume UTC
                    last_calc_time = last_calc_time.replace(tzinfo=datetime.timezone.utc)

                if (datetime.datetime.now(datetime.timezone.utc) - last_calc_time).total_seconds() / 3600 < gex_data_max_age_hours:
                    gex_flip_from_file = gex_data_file_content.get("zero_gamma_level")
                    if gex_flip_from_file is not None:
                         print(f"Loaded GEX flip level {gex_flip_from_file} from {gex_file_path}")
                    else:
                        print(f"GEX flip level is null in {gex_file_path}.")
                else:
                    print(f"GEX data in {gex_file_path} is stale (older than {gex_data_max_age_hours} hours).")
            else:
                print(f"Timestamp missing in {gex_file_path}.")
        else:
            print(f"GEX data file not found at {gex_file_path}.")
    except Exception as e:
        print(f"Error reading or parsing GEX data from {gex_file_path}: {e}")

    if gex_flip_from_file is not None:
        gex_flip = gex_flip_from_file
    elif magic8_data and 'levels' in magic8_data and 'gamma' in magic8_data['levels']:
        gex_flip_candidate = magic8_data['levels']['gamma']
        if gex_flip_candidate is not None:
            gex_flip = gex_flip_candidate
            print(f"Using GEX flip proxy from Magic8 data: {gex_flip}")
        else:
            print("Magic8 data has null gamma level. Using default GEX flip (0).")
            gex_flip = 0
    else:
        print("Warning: GEX flip level not available from file or Magic8 data. Using default (0). Scoring might be affected.")
        gex_flip = 0
    # --- End GEX Flip Logic ---

    try:
        # Fetch ATM options for SPX (0DTE)
        # The ib_client's get_atm_options is async
        atm_options = await ib_client.get_atm_options(symbols=['SPX'], days_to_expiry=0)

        valid_ivs = []
        valid_spreads = []

        if atm_options:
            for opt in atm_options:
                if opt.get('implied_volatility') is not None:
                    valid_ivs.append(opt['implied_volatility'])

                bid = opt.get('bid')
                ask = opt.get('ask')
                if bid is not None and ask is not None and ask > bid:
                    valid_spreads.append(ask - bid)

            if valid_ivs:
                avg_iv = np.mean(valid_ivs)

            if valid_spreads:
                avg_spread = np.mean(valid_spreads)
        else:
            print("Warning: No ATM options data received from IBClient in market_analysis.")

    except ConnectionError as e:
        print(f"IB Connection Error in market_analysis: {e}. Using default values.")
    except Exception as e:
        print(f"Error fetching or processing market data in market_analysis: {e}. Using default values.")

    # Calculate simplified IV rank
    iv_rank = calculate_simple_iv_rank(avg_iv)

    # The gex_analysis.py (copy of SPX-Gamma-Exposure/GEX.py) expects a CBOE file.
    # Adapting it to use live options data from IBClient is complex and likely beyond "lightweight" for MVP.
    # The guide states: "Basic GEX calculation (using SPX-Gamma-Exposure)".
    # If the external tool `SPX-Gamma-Exposure` is run periodically to output a gex_flip level to a file/db,
    # this module could read it. For now, using Magic8's gamma level or a placeholder.

    # The gex_flip value is now determined by the logic above.

    analysis_result = {
        'iv_percentile': iv_rank,  # Simplified rank
        'gex_flip': gex_flip, # gex_flip is already defaulted to 0 if no other source is found
        'spread_avg': avg_spread,
        'current_avg_atm_iv': avg_iv # For informational purposes
    }

    print(f"Market Analysis Result: {analysis_result}")
    return analysis_result

# Example of how it might be called (for testing or understanding)
async def main_test(magic8_sample_data: Optional[Dict] = None):
    from ..config import settings # For IBClient instantiation
    import asyncio # Required for asyncio.run
    # This direct run is for conceptual testing.
    # Real IBClient needs an event loop and proper connection management.

    # Ensure this is run within an asyncio event loop
    # util.patchAsyncio() # if in Jupyter or similar

    # Create a dummy magic8_data if not provided
    if magic8_sample_data is None:
        magic8_sample_data = {
            "spot_price": 5848.66,
            "levels": {"gamma": 5861.65} # Sample gamma level
        }

    # Initialize client (assuming .env is set up for IB connection)
    # This is a simplified setup for testing this module in isolation.
    # In the app, ib_client is managed by the scheduler.
    ib_client_instance = IBClient(host=settings.ib_host, port=settings.ib_port, client_id=settings.ib_client_id + 1) # Use different client ID for test

    analysis = {}
    try:
        # Note: _ensure_connected is usually called by client methods,
        # but for a standalone test, it's good to see the connection attempt.
        # await ib_client_instance._ensure_connected() # This is now handled by get_atm_options
        analysis = await get_market_analysis(ib_client_instance, magic8_sample_data)
        print("Market Analysis Output:", analysis)
    except ConnectionError as e:
        print(f"IB Connection error during test: {e}")
    except Exception as e:
        print(f"Error during market_analysis test: {e}")
    finally:
        await ib_client_instance.disconnect()

if __name__ == '__main__':
    import asyncio # Required for asyncio.run
    # This allows testing this module directly.
    # Ensure you have an event loop if running from a plain Python script.
    # And that IB TWS/Gateway is running and configured.
    # Also, your .env file should be findable from your execution path.

    # Example Magic8 data including a gamma level
    sample_m8_data = {
        "spot_price": 5848.66,
        "trend": "Up",
        "predicted_close": 5849.52,
        "strength": 0.53,
        "range": 10.0,
        "targets": [5850.0, 5860.0],
        "levels": {
            "calls": 5900.0,
            "puts": 5850.0,
            "center": 5875.0,
            "delta": 5846.21,
            "gamma": 5861.65, # This is used as a proxy for gex_flip
            "interest": 5831.99
        }
    }

    # loop = asyncio.get_event_loop() # Deprecated way to get loop in some contexts
    # loop.run_until_complete(main_test(sample_m8_data))

    # Python 3.7+
    asyncio.run(main_test(sample_m8_data))
