import asyncio
from typing import List, Dict, Optional
from ib_async import IB, Stock, Option, MarketOrder, Contract, util, Position, OptionChain, Ticker, Index
from ..unified_config import settings

class IBClient:
    def __init__(self, host: str = settings.ib_host, port: int = settings.ib_port, client_id: int = settings.ib_client_id):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.is_connecting = False
        self.connection_lock = asyncio.Lock()

    async def _ensure_connected(self):
        async with self.connection_lock:
            if not self.ib.isConnected() and not self.is_connecting:
                self.is_connecting = True
                print(f"Connecting to IB: {self.host}:{self.port} with ClientID: {self.client_id}")
                try:
                    await self.ib.connectAsync(self.host, self.port, clientId=self.client_id, timeout=10)
                    print("Successfully connected to IB.")
                except asyncio.TimeoutError:
                    print(f"Timeout connecting to IB on {self.host}:{self.port}. Please ensure TWS/Gateway is running and API connections are enabled.")
                except ConnectionRefusedError:
                     print(f"Connection refused by IB on {self.host}:{self.port}. Check TWS/Gateway API settings.")
                except Exception as e:
                    print(f"Error connecting to IB: {e}")
                finally:
                    self.is_connecting = False

            # If connection attempt failed, it will still be not connected here.
            if not self.ib.isConnected():
                # Raise an exception if we couldn't connect, so calling functions know.
                raise ConnectionError("Failed to connect to IB or not currently connected.")


    async def disconnect(self):
        if self.ib.isConnected():
            print("Disconnecting from IB.")
            self.ib.disconnect()

    async def get_positions(self) -> List[Dict]:
        """Return list of open option positions"""
        await self._ensure_connected()
        positions_data = []

        ib_positions: List[Position] = self.ib.positions()

        for pos in ib_positions:
            contract: Contract = pos.contract
            if contract.secType == 'OPT':
                positions_data.append({
                    'symbol': contract.symbol,
                    'conId': contract.conId,
                    'strike': contract.strike,
                    'right': contract.right, # 'C' or 'P'
                    'expiry': contract.lastTradeDateOrContractMonth,
                    'multiplier': int(contract.multiplier) if contract.multiplier else 100,
                    'quantity': pos.position,
                    'average_cost': pos.avgCost,
                    # Market price and value might require fetching tickers if not directly available
                    # For simplicity, we'll rely on avgCost for now for P&L,
                    # but real P&L requires current market price.
                    # 'market_price': 0, # Placeholder, would need ib.reqMktData
                    # 'market_value': 0, # Placeholder
                    # 'unrealized_pnl': 0, # Placeholder, (market_price * quantity * mult) - (avg_cost * quantity * mult)
                })
        return positions_data

    async def get_atm_options(self, symbols: List[str], days_to_expiry: int = 0) -> List[Dict]:
        """
        Return basic option data for ATM options for the given symbols and DTE.
        Note: Getting precise ATM options and their full data (esp. IV for 0DTE)
        can be complex and might require multiple requests or streaming data.
        This is a simplified version for MVP.
        For 0DTE, lastTradeDateOrContractMonth should be today's date.
        """
        await self._ensure_connected()
        options_data = []

        if not symbols:
            return options_data

        # For 0DTE, expiry date is today. Format: YYYYMMDD
        # This needs to be adjusted for actual trading days / holidays.
        # For simplicity, using util.current_yyyymmdd might not be robust for all cases (e.g. weekends, holidays for non-SPX options)
        # SPX 0DTE options trade on their listed expiry date.
        from datetime import datetime
        expiry_date = datetime.now().strftime('%Y%m%d')


        for symbol_name in symbols:
            # First, get current price of underlying to determine ATM strikes
            underlying_contract = Stock(symbol_name, 'SMART', 'USD') # Assuming SMART exchange
            # Qualify contract for SPX to avoid ambiguity if needed, e.g. for index options
            if symbol_name == "SPX":
                 underlying_contract = Index(symbol_name, 'CBOE', 'USD')


            await self.ib.qualifyContractsAsync(underlying_contract)

            tickers: List[Ticker] = await self.ib.reqTickersAsync(underlying_contract)
            await asyncio.sleep(0.1) # Give some time for ticker data to arrive, though reqTickersAsync should await it.

            spot_price = None
            if tickers and tickers[0] and (tickers[0].marketPrice() or tickers[0].close):
                spot_price = tickers[0].marketPrice() if tickers[0].marketPrice() else tickers[0].close # marketPrice might be NaN outside RTH
                if not spot_price or spot_price <= 0 or str(spot_price) == 'nan': # check for NaN
                    print(f"Could not get valid spot price for {symbol_name}, using placeholder 5000")
                    spot_price = 5000 # Fallback, not ideal
            else:
                print(f"Could not get spot price for {symbol_name}, using placeholder 5000")
                spot_price = 5000 # Fallback, not ideal

            # Determine ATM strikes (e.g., +/- N strikes around spot_price)
            # This is highly simplified. A real implementation would need more robust strike selection.
            atm_strike = round(spot_price / 5) * 5  # Example: round to nearest 5 for SPX

            # Fetch option chain for a range of strikes around ATM
            # For 0DTE, this can be very specific.
            # The guide asks for "ATM options only".
            # Getting option chains and then filtering can be slow.
            # A more direct approach for specific strikes might be better if possible.

            # Let's try to get a few strikes around ATM.
            # For SPX, strikes are usually in 5-point increments.
            strikes_to_check = [atm_strike - 10, atm_strike - 5, atm_strike, atm_strike + 5, atm_strike + 10]

            option_contracts_to_query = []
            for strike in strikes_to_check:
                for right in ['C', 'P']:
                    # For SPX index options, the exchange is CBOE.
                    # For other stock options, it might be different (e.g. SMART)
                    exchange = 'CBOE' if symbol_name == "SPX" else 'SMART'
                    opt_contract = Option(symbol_name, expiry_date, strike, right, exchange, tradingClass=symbol_name)
                    option_contracts_to_query.append(opt_contract)

            if not option_contracts_to_query:
                continue

            try:
                qualified_options = await self.ib.qualifyContractsAsync(*option_contracts_to_query)
            except Exception as e:
                print(f"Error qualifying option contracts for {symbol_name}: {e}")
                continue

            if not qualified_options:
                print(f"No qualified option contracts found for {symbol_name} and strikes {strikes_to_check} for expiry {expiry_date}")
                continue

            # Request market data for these options
            # We need bid, ask, and impliedVolatility
            # Using reqTickersAsync for simplicity, though reqMktData with snapshots might be better for non-streaming.
            # For IV, tick type 24 (Generic Tick Tags) often contains 'IV'.
            # Or, use modelOptionComputation if available for specific contracts.

            tickers_for_options: List[Ticker] = await self.ib.reqTickersAsync(*qualified_options)

            for ticker in tickers_for_options:
                contract: Contract = ticker.contract
                # Implied Volatility might be in ticker.modelGreeks or ticker.impliedVolatility if available directly
                # This part is tricky and highly dependent on TWS version and data subscriptions.
                # modelGreeks are often available if option computation is enabled.
                iv = None
                if ticker.modelGreeks and ticker.modelGreeks.impliedVol is not None and not str(ticker.modelGreeks.impliedVol) == 'nan':
                    iv = ticker.modelGreeks.impliedVol
                elif ticker.impliedVolatility is not None and not str(ticker.impliedVolatility) == 'nan': # Less common for reqTickers
                    iv = ticker.impliedVolatility

                # If IV is still None, we might try to calculate it if we have option price and underlying price
                # This is out of scope for "lightweight" market_analysis module's direct IB call.
                # The market_analysis module itself might do this using py_vollib_vectorized if needed.

                options_data.append({
                    'symbol': contract.symbol,
                    'conId': contract.conId,
                    'strike': contract.strike,
                    'right': contract.right,
                    'expiry': contract.lastTradeDateOrContractMonth,
                    'bid': ticker.bid if ticker.bid != -1 else None,
                    'ask': ticker.ask if ticker.ask != -1 else None,
                    'implied_volatility': iv,
                    'underlying_price_at_fetch': spot_price # For context
                })

        return options_data

async def example_usage():
    # This function is for demonstration and testing from a script.
    # Ensure IB TWS or Gateway is running and API is configured.
    # Ensure .env file has IB_HOST, IB_PORT, IB_CLIENT_ID

    # Note: util.patchAsyncio() should be called if running in Jupyter or certain environments
    # util.patchAsyncio() # if needed

    client = IBClient()
    try:
        await client._ensure_connected() # Call explicitly for example, usually called by methods

        print("\nFetching positions...")
        positions = await client.get_positions()
        if positions:
            for p in positions:
                print(f"  Position: {p.get('quantity')} x {p.get('symbol')} {p.get('expiry')} {p.get('strike')} {p.get('right')}")
        else:
            print("  No open option positions found.")

        print("\nFetching ATM options for SPX (0DTE)...")
        # For 0DTE, days_to_expiry is 0. The function calculates today's date.
        atm_spx_options = await client.get_atm_options(['SPX'], days_to_expiry=0)
        if atm_spx_options:
            for opt in atm_spx_options:
                print(f"  SPX Option: K={opt['strike']} {opt['right']}, Bid={opt['bid']}, Ask={opt['ask']}, IV={opt['implied_volatility']:.4f} (if available)")
        else:
            print("  No ATM SPX options data found.")

    except ConnectionError as e:
        print(f"Main Example Usage: IB Connection Error: {e}")
    except Exception as e:
        print(f"An error occurred in example_usage: {e}")
    finally:
        await client.disconnect()
        # ib_async might keep the event loop running if not stopped explicitly
        # For a script, you might need to cancel pending tasks or stop the loop
        # For example, by calling ib.disconnect() and then ib.wait_for_disconnect()
        # Or, if part of a larger asyncio app, it integrates into that loop.

if __name__ == '__main__':
    # To run this example:
    # 1. Make sure your .env file is in the project root (where you'd run the main app from)
    #    and contains IB_HOST, IB_PORT, IB_CLIENT_ID.
    # 2. IB TWS or Gateway must be running and API connections enabled.
    # 3. Run this file directly (e.g., python -m magic8_companion.modules.ib_client)
    #    This requires Python to handle the module path correctly.

    # util.logToConsole() # Optional: for more detailed ib_async logs
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running (e.g. in Jupyter), use ib.run(example_usage())
            # This is a simplified script execution, assuming no prior loop.
            print("Warning: Loop is already running. This script might behave unexpectedly.")
            task = loop.create_task(example_usage())
            # In a real app, you'd await this task or manage it.
        else:
            loop.run_until_complete(example_usage())
    except KeyboardInterrupt:
        print("Keyboard interrupt caught.")
    finally:
        print("Example usage finished.")
        # Consider loop.close() if this is the only thing running,
        # but be careful if other async tasks are managed elsewhere.
