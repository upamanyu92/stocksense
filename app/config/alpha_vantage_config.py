"""
Alpha Vantage API configuration settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class AlphaVantageConfig:
    """Configuration for Alpha Vantage MCP API integration."""

    # API Key - get a free key at https://www.alphavantage.co/support/#api-key
    API_KEY: str = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')

    # Base URL for Alpha Vantage REST API
    BASE_URL: str = 'https://www.alphavantage.co/query'

    # Rate limiting: free tier allows 5 requests/minute, 500/day
    RATE_LIMIT_PER_MINUTE: int = 5
    RATE_LIMIT_PER_DAY: int = 500

    # Request timeout in seconds
    REQUEST_TIMEOUT: int = 30

    # Cache duration in seconds (1 hour for quotes, 24 hours for fundamentals)
    QUOTE_CACHE_TTL: int = 60          # 1 minute for live quotes
    DAILY_CACHE_TTL: int = 3600        # 1 hour for daily series
    FUNDAMENTAL_CACHE_TTL: int = 86400 # 24 hours for fundamentals & financials
    SENTIMENT_CACHE_TTL: int = 1800    # 30 minutes for news sentiment

    # Default output size for time series ('compact' = 100 data points, 'full' = 20+ years)
    DEFAULT_OUTPUTSIZE: str = 'compact'

    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 12  # seconds between retries (ensures <5 req/min on free tier)

    @classmethod
    def is_configured(cls) -> bool:
        """Return True if a real API key (not demo) is set."""
        return cls.API_KEY not in ('demo', '', None)
