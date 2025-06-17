# Enhanced Configuration for Magic8-Companion

# OI Fetching Configuration
OI_STREAMING_ENABLED = True  # Enable/disable OI streaming attempts
OI_STREAMING_TIMEOUT = 3.0   # Seconds to wait for OI data
USE_VOLUME_FOR_GEX = False   # Use volume instead of OI for GEX calculations
DEFAULT_OI_ESTIMATE = 1000   # Default OI estimate when real data unavailable

# Debug Configuration
DEBUG_OI_FETCHING = True     # Enable detailed OI fetching logs

# Market Data Fallbacks
FALLBACK_OI_SOURCES = [
    "streaming",      # Try streaming first
    "volume",         # Use volume as proxy for OI
    "default"         # Use default estimate
]
