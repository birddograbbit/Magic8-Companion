import pytest
from unittest.mock import AsyncMock, patch
from ib_async import Index
from magic8_companion.modules.ib_client import IBClient
from magic8_companion.unified_config import settings

@pytest.mark.asyncio
async def test_spx_qualification_prefers_cboe():
    client = IBClient()
    mock_ib = AsyncMock()

    async def qualify(contract):
        contract.conId = 99
        return [contract]

    mock_ib.qualifyContractsAsync.side_effect = qualify

    settings.enable_oi_streaming = False
    with patch('magic8_companion.modules.ib_client.get_ib_connection', new=AsyncMock(return_value=mock_ib)):
        contract = await client.qualify_underlying_with_fallback('SPX')
    settings.enable_oi_streaming = True

    assert isinstance(contract, Index)
    assert contract.exchange == 'CBOE'
    first_call = mock_ib.qualifyContractsAsync.call_args_list[0][0][0]
    assert isinstance(first_call, Index)
    assert first_call.exchange == 'CBOE'
