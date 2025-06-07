from typing import List, Dict


class IBClient:
    """Minimal IB client wrapper"""

    def __init__(self, host: str, port: int, client_id: int):
        self.host = host
        self.port = port
        self.client_id = client_id
        # Real integration would initialize ib_async here

    async def get_positions(self) -> List[Dict]:
        """Return list of open option positions"""
        # Placeholder for IB integration
        return []

    async def get_atm_options(self, symbols: List[str], days_to_expiry: int = 0):
        """Return basic option data for market analysis"""
        return []
