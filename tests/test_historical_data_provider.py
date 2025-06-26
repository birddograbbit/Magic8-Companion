import asyncio
import pandas as pd
from magic8_companion.data_providers import IBDataProvider
from magic8_companion.unified_config import settings

def test_ib_provider_fallback():
    settings.ibkr_fallback_to_yahoo = True
    provider = IBDataProvider()
    df = asyncio.run(provider.get_historical_data('SPY', '5m', '1d'))
    assert isinstance(df, pd.DataFrame)
