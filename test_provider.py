import os
from dotenv import load_dotenv
load_dotenv()

# Check environment variables
print("Environment variables:")
print(f"M8C_MARKET_DATA_PROVIDER: {os.getenv('M8C_MARKET_DATA_PROVIDER')}")
print(f"M8C_USE_MOCK_DATA: {os.getenv('M8C_USE_MOCK_DATA')}")
print(f"M8C_USE_IBKR_DATA: {os.getenv('M8C_USE_IBKR_DATA')}")
print(f"M8C_IBKR_HOST: {os.getenv('M8C_IBKR_HOST')}")
print(f"M8C_IBKR_PORT: {os.getenv('M8C_IBKR_PORT')}")

# Test provider selection
from magic8_companion.data_providers import get_provider
provider = get_provider()
print(f"\nSelected provider: {provider.__class__.__name__}")

# Try to connect if IB
if hasattr(provider, 'connect'):
    try:
        provider.connect()
        print("IB connection successful!")
    except Exception as e:
        print(f"IB connection failed: {e}")
